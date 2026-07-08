import sys
import os
from config.settings import GEMINI_API_KEY
from database.supabase import get_all_data_live, send_chat_message
from agents.model_router import ModelRouter

class GeminiCoreAgent:
    def __init__(self):
        self.router = ModelRouter()
        self.last_processed_id = 0

    def execute_thought_cycle(self, user_prompt):
        trades, chat, risiko, knowledge = get_all_data_live()
        system_context = f"""
        Du bist der autonome Chef-Analyst des KIAgent-Handelssystems.
        - Risikostatus: {str(risiko[:1] if risiko else 'OPEN')}
        - Bekanntes Wissen: {str(knowledge)}
        - Offene Positionen: {str(trades[:5] if trades else 'Keine aktiven Trades')}
        """
        # JETZT: CHAT LÄUFT EXKLUSIV ÜBER GEMINI (Damit Groq völlig frei für Trading ist!)
        answer, model_used = self.router.route(user_prompt, system_context, preferred_model="gemini")
        return answer

    def process_live_chat(self, last_processed_id=0):
        try:
            _, chat, _, _ = get_all_data_live()
            if not chat or len(chat) == 0: return None
            chat.sort(key=lambda x: x.get('id', 0))
            new_messages = [m for m in chat if m.get('id', 0) > last_processed_id and m.get('role') == 'user']
            if not new_messages: return last_processed_id
            latest = new_messages[-1]
            user_input = latest.get('content', '')
            antwort = self.execute_thought_cycle(user_input)
            send_chat_message("assistant", antwort)
            return latest.get('id', last_processed_id)
        except Exception as e:
            print(f"❌ Kritischer Absturz im Agenten-Chat-Loop: {e}", flush=True)
            return None
