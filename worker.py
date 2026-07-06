def process_chat():
    try:
        # FIX: Geändert von Chatnachrichten auf chat_messages
        messages = requests.get(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS).json()
        if messages and len(messages) > 0:
            # FIX: Sortierung nach 'id' statt 'Ausweis'
            latest_msg = sorted(messages, key=lambda x: x.get('id', 0))[-1]
            if latest_msg["role"] == "user":
                user_input = latest_msg["content"]
                
                # Hier holen wir das echte Sentiment über Gemini ab
                system_context = "Du bist der unfehlbare Krypto-Trading-Experte. Antworte kurz auf Deutsch."
                bot_response = ask_gemini_expert(f"{system_context}\n\nMaster schreibt: {user_input}")
                
                # FIX: Antwort in die korrekte Tabelle posten
                requests.post(f"{SUPABASE_URL}/rest/v1/chat_messages", headers=HEADERS, json={
                    "role": "assistant", 
                    "content": bot_response
                })
    except Exception as e: 
        print(f"Fehler im Chat-Loop: {e}")
