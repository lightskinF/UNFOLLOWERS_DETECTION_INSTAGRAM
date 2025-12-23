import requests
import re
import json
import time
import random
import os
import logging
from typing import List, Optional
from dataclasses import dataclass

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class InstagramConfig:
    """Configurazione per Instagram scraping"""
    user_agents: List[str]
    query_hashes: dict
    base_headers: dict
    request_delay_min: float = 2.0
    request_delay_max: float = 5.0
    max_retries: int = 3
    batch_size: int = 50

class InstagramScraper:
    def __init__(self, session_id: str, config: InstagramConfig):
        self.session_id = session_id
        self.config = config
        self.cookies = {"sessionid": session_id}
        self.session = requests.Session()
        
    def get_with_rotation(self, url: str) -> requests.Response:
        """GET con user-agent random e gestione errori"""
        for attempt in range(self.config.max_retries):
            try:
                headers = self.config.base_headers.copy()
                headers["User-Agent"] = random.choice(self.config.user_agents)
                
                response = self.session.get(url, headers=headers, cookies=self.cookies)
                
                # Controllo status code
                if response.status_code == 429:
                    wait_time = random.uniform(30, 60)
                    logger.warning(f"Rate limit raggiunto, attendo {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 200:
                    # Pausa random tra le richieste
                    delay = random.uniform(self.config.request_delay_min, 
                                         self.config.request_delay_max)
                    time.sleep(delay)
                    return response
                else:
                    logger.warning(f"Status code: {response.status_code}, tentativo {attempt + 1}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Errore richiesta (tentativo {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(random.uniform(5, 10))
                    
        raise Exception(f"Impossibile completare la richiesta dopo {self.config.max_retries} tentativi")

    def get_user_id_from_html(self, username: str) -> str:
        """Estrae l'ID utente dall'HTML del profilo"""
        url = f"https://www.instagram.com/{username}/"
        
        try:
            headers = {"User-Agent": random.choice(self.config.user_agents)}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Prova diversi pattern per estrarre l'ID
            patterns = [
                r'"profilePage_(\d+)"',
                r'"id":"(\d+)".*"username":"' + re.escape(username) + '"',
                r'"user_id":"(\d+)"'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    user_id = match.group(1)
                    logger.info(f"ID utente trovato: {user_id}")
                    return user_id
                    
            # Se non trova l'ID con i pattern, prova a estrarre dal JSON
            json_match = re.search(r'window\._sharedData\s*=\s*({.+?});', response.text)
            if json_match:
                shared_data = json.loads(json_match.group(1))
                entry_data = shared_data.get('entry_data', {})
                profile_page = entry_data.get('ProfilePage', [])
                if profile_page:
                    user = profile_page[0].get('graphql', {}).get('user', {})
                    if user.get('id'):
                        return user['id']
                        
        except Exception as e:
            logger.error(f"Errore nel recupero ID utente: {e}")
            
        raise ValueError("❌ Impossibile trovare l'ID utente")

    def scrape_list(self, user_id: str, list_type: str) -> List[str]:
        """Scarica followers o following con gestione errori migliorata"""
        if list_type not in ['followers', 'following']:
            raise ValueError("list_type deve essere 'followers' o 'following'")
            
        query_hash = self.config.query_hashes[list_type]
        results = []
        end_cursor = ""
        has_next_page = True
        page_count = 0
        
        logger.info(f"🔄 Inizio raccolta {list_type}...")
        
        while has_next_page:
            try:
                variables = {
                    "id": user_id,
                    "include_reel": True,
                    "fetch_mutual": False,
                    "first": self.config.batch_size,
                    "after": end_cursor
                }
                
                url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables={json.dumps(variables)}"
                response = self.get_with_rotation(url)
                data = response.json()
                
                if "data" not in data or "user" not in data["data"]:
                    logger.error("Struttura dati non valida o limite raggiunto")
                    break
                
                user_data = data["data"]["user"]
                if list_type == "followers":
                    edge_key = "edge_followed_by"
                else:
                    edge_key = "edge_follow"
                
                if edge_key not in user_data:
                    logger.error(f"Chiave {edge_key} non trovata nei dati")
                    break
                    
                edges = user_data[edge_key]["edges"]
                page_info = user_data[edge_key]["page_info"]
                
                batch_usernames = []
                for edge in edges:
                    username = edge["node"]["username"]
                    batch_usernames.append(username)
                    results.append(username)
                
                page_count += 1
                logger.info(f"📄 Pagina {page_count}: +{len(batch_usernames)} utenti (totale: {len(results)})")
                
                has_next_page = page_info["has_next_page"]
                end_cursor = page_info.get("end_cursor", "")
                
            except json.JSONDecodeError as e:
                logger.error(f"Errore parsing JSON: {e}")
                break
            except Exception as e:
                logger.error(f"Errore durante scraping: {e}")
                break
                
        logger.info(f"✅ Raccolta {list_type} completata: {len(results)} utenti")
        return results

    def find_non_followers(self, username: str) -> List[str]:
        """Trova gli utenti che non ti seguono"""
        try:
            logger.info(f"🔍 Analisi per l'utente: {username}")
            
            # Recupera ID utente
            user_id = self.get_user_id_from_html(username)
            
            # Raccoglie followers e following
            followers = self.scrape_list(user_id, "followers")
            following = self.scrape_list(user_id, "following")
            
            # Calcola differenze
            non_followers = list(set(following) - set(followers))
            mutual_follows = list(set(following) & set(followers))
            
            # Log statistiche
            logger.info(f"📊 Statistiche:")
            logger.info(f"   Followers: {len(followers)}")
            logger.info(f"   Following: {len(following)}")
            logger.info(f"   Seguono a vicenda: {len(mutual_follows)}")
            logger.info(f"   Non ti seguono: {len(non_followers)}")
            
            return non_followers
            
        except Exception as e:
            logger.error(f"Errore nell'analisi: {e}")
            raise

def save_results(non_followers: List[str], filename: str = "non_followers.txt"):
    """Salva i risultati in un file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Utenti che non ti seguono ({len(non_followers)}):\n")
            f.write("=" * 50 + "\n")
            for username in sorted(non_followers):
                f.write(f"{username}\n")
        logger.info(f"💾 Risultati salvati in '{filename}'")
    except Exception as e:
        logger.error(f"Errore nel salvataggio: {e}")

def load_session_from_env() -> Optional[str]:
    """Carica session ID dalle variabili d'ambiente"""
    return os.getenv('INSTAGRAM_SESSION_ID')

def main():
    # Configurazione
    config = InstagramConfig(
        user_agents=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ],
        query_hashes={
            "followers": "c76146de99bb02f6415203be841dd25a",
            "following": "d04b0a864b4b54837c0d870b0e77e076"
        },
        base_headers={
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": "missing",  # Potrebbe essere necessario
        }
    )
    
    # Carica session ID
    session_id = load_session_from_env()
    if not session_id:
        session_id = input("🔐 Inserisci il tuo Session ID di Instagram: ").strip()
    
    if not session_id:
        logger.error("❌ Session ID necessario per continuare")
        return
    
    # Input username
    username = input("👤 Inserisci il tuo username Instagram: ").strip()
    if not username:
        logger.error("❌ Username necessario")
        return
    
    try:
        # Crea scraper ed esegui analisi
        scraper = InstagramScraper(session_id, config)
        non_followers = scraper.find_non_followers(username)
        
        # Mostra risultati
        print(f"\n🔍 RISULTATI per @{username}")
        print("=" * 50)
        print(f"Utenti che segui ma che NON ti seguono: {len(non_followers)}")
        print("-" * 30)
        
        if non_followers:
            for i, user in enumerate(sorted(non_followers), 1):
                print(f"{i:3d}. {user}")
        else:
            print("🎉 Tutti quelli che segui ti seguono anche!")
        
        # Salva risultati
        if non_followers:
            save_results(non_followers)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Operazione interrotta dall'utente")
    except Exception as e:
        logger.error(f"❌ Errore generale: {e}")

if __name__ == "__main__":
    main()