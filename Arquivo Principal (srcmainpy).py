import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import pytz
from AdvancedPriceTracker import AdvancedPriceTracker

# Configuração da página
st.set_page_config(
    page_title="🛒 PriceTracker Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO CSS ---
st.markdown("""
<style>
    .highlight {
        background-color: #fff2cc;
        padding: 2px 5px;
        border-radius: 3px;
    }
    .promo-badge {
        background-color: #27ae60;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.8em;
    }
    .price-up {
        color: #e74c3c;
        font-weight: bold;
    }
    .price-down {
        color: #2ecc71;
        font-weight: bold;
    }
    .stAlert {
        border-left: 4px solid #3498db;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Inicializa o estado da sessão"""
    if 'tracker' not in st.session_state:
        st.session_state.tracker = AdvancedPriceTracker()
        st.session_state.history = pd.DataFrame()
        st.session_state.last_run = None
        st.session_state.run_automatically = True

def setup_sidebar():
    """Configura a barra lateral"""
    with st.sidebar:
        st.title("⚙️ Configurações")
        
        with st.expander("🔍 Parâmetros de Busca", expanded=True):
            product_query = st.text_input("Produto para monitorar", "iPhone 13")
            num_pages = st.slider("Número de páginas do Google", 1, 10, 2)
            update_interval = st.select_slider(
                "Intervalo de atualização", 
                options=[1, 5, 15, 30, 60],
                value=15,
                format_func=lambda x: f"{x} min"
            )
        
        with st.expander("📧 Alertas por E-mail", expanded=False):
            email_alerts = st.checkbox("Ativar alertas")
            if email_alerts:
                sender_email = st.text_input("Seu e-mail (Gmail)")
                sender_password = st.text_input("Senha do e-mail", type="password")
                receiver_email = st.text_input("E-mail destinatário")
                alert_threshold = st.slider("Limite de desconto para alerta (%)", 5, 50, 15)
        
        st.divider()
        st.markdown("🔄 Última atualização:")
        last_update_placeholder = st.empty()
        st.checkbox("Atualização automática", value=st.session_state.run_automatically, key="auto_update")
    
    return {
        'product_query': product_query,
        'num_pages': num_pages,
        'update_interval': update_interval,
        'email_alerts': email_alerts,
        'sender_email': sender_email if email_alerts else None,
        'sender_password': sender_password if email_alerts else None,
        'receiver_email': receiver_email if email_alerts else None,
        'alert_threshold': alert_threshold if email_alerts else None,
        'last_update_placeholder': last_update_placeholder
    }

def run_price_check(config):
    """Executa a verificação de preços"""
    with st.spinner("🔄 Buscando dados atualizados..."):
        try:
            tracker = st.session_state.tracker
            product_query = config['product_query']
            
            # Coleta de dados
            tracker.get_google_shopping_results(product_query, config['num_pages'])
            df = tracker.save_results(product_query)
            
            if df is not None and not df.empty:
                # Atualiza histórico
                timestamp = datetime.now(pytz.timezone('America/Sao_Paulo'))
                df['timestamp'] = timestamp
                st.session_state.history = pd.concat([st.session_state.history, df])
                st.session_state.last_run = timestamp
                config['last_update_placeholder'].markdown(f"⏱️ {timestamp.strftime('%d/%m/%Y %H:%M:%S')}")
                
                # Verifica promoções para alertas
                if config['email_alerts']:
                    tracker.email_config = {
                        'sender': config['sender_email'],
                        'password': config['sender_password'],
                        'receiver': config['receiver_email'],
                        'smtp_server': 'smtp.gmail.com',
                        'smtp_port': 587,
                        'threshold': config['alert_threshold']
                    }
                    
                    discounts = df[df['Desconto'].str.contains('%', na=False)]
                    if not discounts.empty:
                        attachments = []
                        trend_img = tracker.generate_price_trends(product_query)
                        if trend_img:
                            attachments.append(trend_img)
                        tracker.send_email_alert(product_query, attachments)
                
                return True
            
        except Exception as e:
            st.error(f"Erro na coleta: {str(e)}")
            return False
    return False

def display_overview_tab(current_data):
    """Exibe a aba de visão geral"""
    with st.expander("📊 Visão Geral do Mercado", expanded=True):
        # Métricas rápidas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ofertas encontradas", len(current_data))
        with col2:
            min_price = current_data['Preço_Numerico'].min()
            st.metric("Menor preço", f"R$ {min_price:,.2f}")
        with col3:
            discounts = current_data[current_data['Desconto'].str.contains('%', na=False)]
            st.metric("Promoções", len(discounts))
        
        # Top 10 ofertas
        st.subheader("🏆 Top 10 Melhores Ofertas")
        top10 = current_data.sort_values('Preço_Numerico').head(10)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = ['#27ae60' if '%' in str(d) else '#3498db' for d in top10['Desconto']]
        ax.barh(
            top10['Produto'].str[:30] + " (" + top10['Loja'].str[:10] + ")",
            top10['Preço_Numerico'],
            color=colors
        )
        ax.set_xlabel("Preço (R$)")
        ax.set_title("Comparação de Preços - Top 10")
        st.pyplot(fig)
        
        # Destaque para promoções
        if not discounts.empty:
            st.subheader("🔥 Destaques Promocionais")
            cols = st.columns(2)
            for idx, (_, row) in enumerate(discounts.head(4).iterrows()):
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.markdown(f"**{row['Produto'][:50]}**")
                        st.markdown(f"🏪 **{row['Loja']}**")
                        st.markdown(f"🔹 <span class='price-down'>Desconto: {row['Desconto']}</span>", unsafe_allow_html=True)
                        st.markdown(f"💰 ~~R$ {float(row['Preço_Original']):,.2f}~~ → **R$ {float(row['Preço_Numerico']):,.2f}**")

def display_trends_tab():
    """Exibe a aba de tendências"""
    with st.expander("📈 Análise de Tendências", expanded=True):
        if len(st.session_state.history) > 1:
            tracker = st.session_state.tracker
            product_query = st.session_state.get('product_query', 'Produto')
            
            # Gráfico de tendência temporal
            st.subheader("Evolução Histórica de Preços")
            trend_img = tracker.generate_price_trends(product_query)
            if trend_img:
                st.image(trend_img, use_column_width=True)
            
            # Análise de variação
            st.subheader("Variação Percentual")
            price_changes = tracker.calculate_price_changes(st.session_state.history)
            st.dataframe(price_changes.style.format({
                'Variação': '{:.2f}%',
                'Preço_Atual': 'R$ {:.2f}',
                'Preço_Anterior': 'R$ {:.2f}'
            }))
        else:
            st.warning("Colete mais dados para habilitar a análise de tendências")

def display_details_tab(current_data):
    """Exibe a aba de detalhes"""
    with st.expander("🔍 Detalhes Completos", expanded=True):
        # Filtros interativos
        with st.expander("⚙️ Filtros Avançados", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                min_price = st.number_input("Preço mínimo", value=0)
                max_price = st.number_input("Preço máximo", value=current_data['Preço_Numerico'].max())
            with col2:
                stores = st.multiselect("Lojas", options=current_data['Loja'].unique())
                only_discounts = st.checkbox("Apenas promoções")
        
        # Aplicar filtros
        filtered_data = current_data[
            (current_data['Preço_Numerico'] >= min_price) & 
            (current_data['Preço_Numerico'] <= max_price)
        ]
        if stores:
            filtered_data = filtered_data[filtered_data['Loja'].isin(stores)]
        if only_discounts:
            filtered_data = filtered_data[filtered_data['Desconto'].str.contains('%', na=False)]
        
        # Exibição dos dados
        st.dataframe(
            filtered_data.sort_values('Preço_Numerico')[['Produto', 'Loja', 'Preço_Atual', 'Desconto', 'Link']],
            column_config={
                "Produto": "Produto",
                "Loja": "Loja",
                "Preço_Atual": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                "Desconto": "Desconto",
                "Link": st.column_config.LinkColumn("Link")
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

def main():
    """Função principal"""
    st.title("🛒 PriceTracker Pro")
    st.markdown("""
    **Acompanhamento em tempo real** dos melhores preços do mercado com alertas automáticos.
    """)
    
    # Inicialização e configuração
    initialize_session_state()
    config = setup_sidebar()
    
    # Controles de execução
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**Monitorando:** `{config['product_query']}` | **Páginas:** `{config['num_pages']}` | **Intervalo:** `{config['update_interval']} min`")
    with col2:
        if st.button("🔄 Executar Agora", type="primary"):
            if run_price_check(config):
                st.success("Dados atualizados com sucesso!")
            else:
                st.error("Falha ao atualizar dados")
    
    # Atualização automática
    if st.session_state.run_automatically and st.session_state.last_run:
        next_run = st.session_state.last_run + timedelta(minutes=config['update_interval'])
        if datetime.now(pytz.timezone('America/Sao_Paulo')) >= next_run:
            run_price_check(config)
    
    # Exibição dos dados
    if st.session_state.last_run and not st.session_state.history.empty:
        current_data = st.session_state.history[
            st.session_state.history['timestamp'] == st.session_state.last_run
        ].copy()
        
        # Pré-processamento dos dados
        current_data['Desconto_Num'] = current_data['Desconto'].str.extract(r'(\d+)').astype(float)
        
        # Criação das abas
        tab1, tab2, tab3 = st.tabs(["Visão Geral", "Tendência", "Detalhes"])
        
        with tab1:
            display_overview_tab(current_data)
        
        with tab2:
            display_trends_tab()
        
        with tab3:
            display_details_tab(current_data)
    else:
        st.info("Execute o monitoramento pela primeira vez para visualizar os dados")

if __name__ == "__main__":
    main()