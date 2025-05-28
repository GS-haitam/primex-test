# =============================================================================
# MODÈLE DE COMPTABILITÉ BTP - VERSION CLOUD
# Optimisé pour Streamlit Community Cloud
# =============================================================================

import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# Configuration de la page (DOIT être en premier)
st.set_page_config(
    page_title="Comptabilité BTP Laayoune",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CLASSE COMPTABILITÉ (Adaptée pour le cloud)
# =============================================================================

class ComptabiliteBTP:
    def __init__(self, db_name="comptabilite_btp.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Créer la base de données et les tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Table principale des transactions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_transaction DATE NOT NULL,
            compte_debit TEXT NOT NULL,
            compte_credit TEXT NOT NULL,
            montant REAL NOT NULL,
            description TEXT NOT NULL,
            type_transaction TEXT NOT NULL,
            reference_bdc TEXT,
            responsable TEXT,
            statut TEXT DEFAULT 'Validé',
            date_saisie TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Table des comptes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS comptes (
            code_compte TEXT PRIMARY KEY,
            nom_compte TEXT NOT NULL,
            type_compte TEXT NOT NULL,
            solde_actuel REAL DEFAULT 0
        )
        ''')
        
        # Initialiser les comptes si vides
        comptes_principaux = [
            ('INVEST', 'Investissement', 'ACTIF'),
            ('SYS_BDC', 'Système BDC', 'ACTIF'),
            ('DEP_OP', 'Dépenses Opérationnelles', 'CHARGE'),
            ('CHARGE_FIX', 'Charges Fixes', 'CHARGE'),
            ('RECETTES', 'Recettes', 'PRODUIT')
        ]
        
        cursor.execute("SELECT COUNT(*) FROM comptes")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO comptes (code_compte, nom_compte, type_compte) VALUES (?, ?, ?)",
                comptes_principaux
            )
        
        conn.commit()
        conn.close()
    
    def ajouter_transaction(self, date_trans, compte_debit, compte_credit, 
                           montant, description, type_trans, ref_bdc=None, responsable=None):
        """Ajouter une nouvelle transaction"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO transactions 
            (date_transaction, compte_debit, compte_credit, montant, description, 
             type_transaction, reference_bdc, responsable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date_trans, compte_debit, compte_credit, montant, description, 
                  type_trans, ref_bdc, responsable))
            
            # Mettre à jour les soldes
            cursor.execute('UPDATE comptes SET solde_actuel = solde_actuel + ? WHERE code_compte = ?', 
                          (montant, compte_debit))
            cursor.execute('UPDATE comptes SET solde_actuel = solde_actuel - ? WHERE code_compte = ?', 
                          (montant, compte_credit))
            
            conn.commit()
            return True, "Transaction ajoutée avec succès"
        
        except Exception as e:
            conn.rollback()
            return False, f"Erreur: {str(e)}"
        
        finally:
            conn.close()
    
    def get_transactions(self, limit=None):
        """Récupérer les transactions"""
        conn = sqlite3.connect(self.db_name)
        query = '''
        SELECT id, date_transaction, compte_debit, compte_credit, montant, 
               description, type_transaction, reference_bdc, responsable, statut
        FROM transactions 
        ORDER BY date_transaction DESC
        '''
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            df = pd.read_sql_query(query, conn)
        except:
            df = pd.DataFrame()
        
        conn.close()
        return df
    
    def get_soldes_comptes(self):
        """Récupérer les soldes de tous les comptes"""
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query('''
            SELECT code_compte, nom_compte, type_compte, solde_actuel
            FROM comptes
            ORDER BY code_compte
            ''', conn)
        except:
            df = pd.DataFrame()
        
        conn.close()
        return df
    
    def supprimer_transaction(self, transaction_id):
        """Supprimer une transaction"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT compte_debit, compte_credit, montant FROM transactions WHERE id = ?', 
                          (transaction_id,))
            result = cursor.fetchone()
            
            if result:
                compte_debit, compte_credit, montant = result
                
                # Inverser les mouvements
                cursor.execute('UPDATE comptes SET solde_actuel = solde_actuel - ? WHERE code_compte = ?', 
                              (montant, compte_debit))
                cursor.execute('UPDATE comptes SET solde_actuel = solde_actuel + ? WHERE code_compte = ?', 
                              (montant, compte_credit))
                
                cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
                
                conn.commit()
                return True, "Transaction supprimée avec succès"
            else:
                return False, "Transaction non trouvée"
        
        except Exception as e:
            conn.rollback()
            return False, f"Erreur: {str(e)}"
        
        finally:
            conn.close()
    
    def get_synthese_mensuelle(self, annee=None, mois=None):
        """Synthèse mensuelle"""
        if not annee:
            annee = datetime.now().year
        if not mois:
            mois = datetime.now().month
        
        conn = sqlite3.connect(self.db_name)
        
        try:
            query = '''
            SELECT type_transaction, SUM(montant) as total
            FROM transactions 
            WHERE strftime('%Y', date_transaction) = ? 
            AND strftime('%m', date_transaction) = ?
            GROUP BY type_transaction
            '''
            df = pd.read_sql_query(query, conn, params=(str(annee), f"{mois:02d}"))
        except:
            df = pd.DataFrame()
        
        conn.close()
        return df

# =============================================================================
# AUTHENTIFICATION SIMPLE
# =============================================================================

def check_password():
    """Vérification mot de passe simple"""
    def password_entered():
        if st.session_state["password"] == "btp2024":  # Changez ce mot de passe
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("### 🔐 Accès Sécurisé")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        st.info("💡 Entrez le mot de passe pour accéder à l'application")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        st.error("❌ Mot de passe incorrect")
        return False
    else:
        return True

# =============================================================================
# INTERFACE PRINCIPALE
# =============================================================================

def main():
    """Interface principale"""
    
    # Vérification mot de passe
    if not check_password():
        st.stop()
    
    # Initialiser la comptabilité
    if 'compta' not in st.session_state:
        st.session_state.compta = ComptabiliteBTP()
    
    compta = st.session_state.compta
    
    # En-tête
    st.title("🏗️ Comptabilité BTP - Laayoune")
    st.markdown("### Système de Gestion Financière")
    st.markdown("---")
    
    # Navigation
    st.sidebar.title("📋 Navigation")
    page = st.sidebar.selectbox(
        "Choisir une section",
        ["🏠 Tableau de Bord", "➕ Nouvelle Transaction", "📊 Analyses", "⚙️ Gestion"]
    )
    
    # Informations de connexion
    st.sidebar.markdown("---")
    st.sidebar.info("🌐 **Mode Cloud Activé**\n📡 Données synchronisées")
    
    # =============================================================================
    # TABLEAU DE BORD
    # =============================================================================
    
    if page == "🏠 Tableau de Bord":
        st.header("📊 Tableau de Bord Financier")
        
        # Récupérer les soldes
        soldes = compta.get_soldes_comptes()
        
        if not soldes.empty:
            # Métriques principales
            col1, col2, col3, col4, col5 = st.columns(5)
            
            comptes_data = {row['code_compte']: row['solde_actuel'] for _, row in soldes.iterrows()}
            
            with col1:
                invest = comptes_data.get('INVEST', 0)
                delta_invest = invest * 0.1  # Simulation delta
                st.metric("💰 Investissement", f"{invest:,.0f} DH", delta=f"{delta_invest:.0f}")
            
            with col2:
                sys_bdc = comptes_data.get('SYS_BDC', 0)
                st.metric("🔧 Système BDC", f"{sys_bdc:,.0f} DH")
            
            with col3:
                dep_op = abs(comptes_data.get('DEP_OP', 0))
                st.metric("📤 Dépenses Opé.", f"{dep_op:,.0f} DH")
            
            with col4:
                charges = abs(comptes_data.get('CHARGE_FIX', 0))
                st.metric("🏢 Charges Fixes", f"{charges:,.0f} DH")
            
            with col5:
                recettes = abs(comptes_data.get('RECETTES', 0))
                st.metric("💵 Recettes", f"{recettes:,.0f} DH")
            
            st.markdown("---")
            
            # Graphiques
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Répartition des Comptes")
                soldes_viz = soldes.copy()
                soldes_viz['solde_abs'] = soldes_viz['solde_actuel'].abs()
                soldes_viz = soldes_viz[soldes_viz['solde_abs'] > 0]
                
                if not soldes_viz.empty:
                    fig = px.pie(soldes_viz, values='solde_abs', names='nom_compte',
                               title="Distribution des Soldes",
                               color_discrete_sequence=px.colors.qualitative.Set3)
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune donnée à afficher")
            
            with col2:
                st.subheader("📈 Évolution Récente")
                transactions = compta.get_transactions(10)
                if not transactions.empty:
                    # Graphique des transactions récentes
                    fig = px.bar(transactions.head(5), 
                               x='date_transaction', 
                               y='montant',
                               color='type_transaction',
                               title="5 Dernières Transactions")
                    fig.update_layout(xaxis_title="Date", yaxis_title="Montant (DH)")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Aucune transaction enregistrée")
        
        # Dernières transactions
        st.subheader("📋 Activité Récente")
        transactions = compta.get_transactions(5)
        if not transactions.empty:
            st.dataframe(
                transactions[['date_transaction', 'description', 'montant', 'type_transaction']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("💡 Commencez par ajouter votre première transaction")
    
    # =============================================================================
    # NOUVELLE TRANSACTION
    # =============================================================================
    
    elif page == "➕ Nouvelle Transaction":
        st.header("➕ Ajouter une Transaction")
        
        with st.form("nouvelle_transaction", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                date_trans = st.date_input("📅 Date", value=date.today())
                
                compte_debit = st.selectbox("📤 Compte à Débiter", [
                    "INVEST", "SYS_BDC", "DEP_OP", "CHARGE_FIX", "RECETTES"
                ], help="Compte qui donne l'argent")
                
                compte_credit = st.selectbox("📥 Compte à Créditer", [
                    "INVEST", "SYS_BDC", "DEP_OP", "CHARGE_FIX", "RECETTES"
                ], help="Compte qui reçoit l'argent")
                
                montant = st.number_input("💰 Montant (DH)", min_value=0.0, step=100.0)
            
            with col2:
                description = st.text_area("📝 Description", height=100,
                                         placeholder="Ex: Achat peinture pour BDC001")
                
                type_trans = st.selectbox("🏷️ Type", [
                    "BDC", "Investissement", "Charge Fixe", "Achat Matériel", "Autre"
                ])
                
                ref_bdc = st.text_input("🔗 Référence BDC", placeholder="Ex: BDC001")
                
                responsable = st.text_input("👤 Responsable", placeholder="Nom de la personne")
            
            submitted = st.form_submit_button("💾 Enregistrer", type="primary")
            
            if submitted:
                if compte_debit == compte_credit:
                    st.error("❌ Les comptes débit et crédit doivent être différents")
                elif montant <= 0:
                    st.error("❌ Le montant doit être positif")
                elif not description.strip():
                    st.error("❌ La description est obligatoire")
                else:
                    success, message = compta.ajouter_transaction(
                        date_trans, compte_debit, compte_credit, montant,
                        description, type_trans, ref_bdc, responsable
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
    
    # =============================================================================
    # ANALYSES
    # =============================================================================
    
    elif page == "📊 Analyses":
        st.header("📊 Analyses Financières")
        
        col1, col2 = st.columns(2)
        with col1:
            annee = st.selectbox("📅 Année", [2024, 2025], index=0)
        with col2:
            mois = st.selectbox("📅 Mois", list(range(1, 13)), index=datetime.now().month-1)
        
        st.subheader(f"📈 Synthèse {mois:02d}/{annee}")
        
        synthese = compta.get_synthese_mensuelle(annee, mois)
        
        if not synthese.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(synthese, use_container_width=True, hide_index=True)
                
                total = synthese['total'].sum()
                st.metric("💰 Total Transactions", f"{total:,.0f} DH")
            
            with col2:
                fig = px.bar(synthese, x='type_transaction', y='total',
                           title=f"Transactions par Type - {mois:02d}/{annee}",
                           color='total',
                           color_continuous_scale='Viridis')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"📋 Aucune transaction pour {mois:02d}/{annee}")
        
        # Analyse des comptes
        st.markdown("---")
        st.subheader("💼 État des Comptes")
        
        soldes = compta.get_soldes_comptes()
        if not soldes.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.dataframe(soldes, use_container_width=True, hide_index=True)
            
            with col2:
                fig = px.bar(soldes, x='nom_compte', y='solde_actuel',
                           title="Soldes par Compte",
                           color='solde_actuel',
                           color_continuous_scale='RdYlGn')
                fig.update_xaxis(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)
    
    # =============================================================================
    # GESTION
    # =============================================================================
    
    elif page == "⚙️ Gestion":
        st.header("⚙️ Gestion du Système")
        
        # Statistiques
        st.subheader("📊 Statistiques Générales")
        
        transactions = compta.get_transactions()
        soldes = compta.get_soldes_comptes()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            nb_trans = len(transactions) if not transactions.empty else 0
            st.metric("📝 Transactions", nb_trans)
        
        with col2:
            if not soldes.empty:
                total_actifs = soldes[soldes['solde_actuel'] > 0]['solde_actuel'].sum()
                st.metric("💰 Total Actifs", f"{total_actifs:,.0f} DH")
        
        with col3:
            if not soldes.empty:
                total_passifs = abs(soldes[soldes['solde_actuel'] < 0]['solde_actuel'].sum())
                st.metric("💸 Total Dépenses", f"{total_passifs:,.0f} DH")
        
        with col4:
            if not transactions.empty:
                derniere_trans = transactions['date_transaction'].iloc[0] if len(transactions) > 0 else "Aucune"
                st.metric("📅 Dernière Transaction", derniere_trans)
        
        st.markdown("---")
        
        # Gestion des transactions
        st.subheader("🗑️ Supprimer une Transaction")
        
        if not transactions.empty:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.dataframe(transactions[['id', 'date_transaction', 'description', 'montant']].head(10), 
                           use_container_width=True, hide_index=True)
            
            with col2:
                trans_id = st.number_input("ID à supprimer", min_value=1, step=1)
                if st.button("🗑️ Supprimer", type="secondary"):
                    success, message = compta.supprimer_transaction(trans_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Aucune transaction à gérer")
        
        # Informations système
        st.markdown("---")
        st.subheader("ℹ️ Informations Système")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("🌐 **Hébergement** : Streamlit Community Cloud")
            st.info("💾 **Base de Données** : SQLite")
        
        with col2:
            st.info("🔒 **Sécurité** : Mot de passe protégé")
            st.info("📱 **Compatibilité** : Multi-dispositifs")

# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    main()
