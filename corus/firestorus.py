import os
from typing import List, Dict, Any, Optional
import firebase_admin
from firebase_admin import credentials, firestore


import threading

class FirestoreClient:

        def get_last_message_timestamp(self, collection_name: str, server_id: str, channel_id: str) -> float:
            """
            Retourne le timestamp du dernier message enregistré pour un channel donné, ou None si aucun message.
            """
            # Accès à la sous-collection des messages du channel
            messages_ref = (
                self.db.collection(collection_name)
                .document(str(server_id))
                .collection(str(channel_id))
            )
            # On trie par timestamp décroissant et on prend le premier
            query = messages_ref.order_by("timestamp", direction="DESCENDING").limit(1)
            docs = list(query.stream())
            if not docs:
                return None
            data = docs[0].to_dict()
            return data.get("timestamp")
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, cred_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, cred_path: Optional[str] = None):
        if getattr(self, '_initialized', False):
            return
        if not firebase_admin._apps:
            if cred_path is None:
                cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self._initialized = True

    def close(self):
        # Firebase Admin SDK ne propose pas de méthode explicite pour fermer la connexion,
        # mais on peut logguer la fermeture et nettoyer l'instance si besoin.
        import logging
        logging.info("FirestoreClient: fermeture de la connexion (nettoyage instance)")
        FirestoreClient._instance = None
        self._initialized = False


    def insert_message(self, collection_name: str, message: Dict[str, Any]):
        server_id = str(message.get("server_id"))
        channel_id = str(message.get("channel_id"))
        msg_id = str(message.get("message_id"))
        self.db.collection(collection_name)\
            .document(server_id)\
            .collection(channel_id)\
            .document(msg_id)\
            .set(message)


    def insert_messages(self, collection_name: str, messages: List[Dict[str, Any]]):
        # Firestore batch write limit: 500 ops, but we use 400 to stay safe (and avoid payload size limit)
        BATCH_SIZE = 400
        for i in range(0, len(messages), BATCH_SIZE):
            batch = self.db.batch()
            for message in messages[i:i+BATCH_SIZE]:
                server_id = str(message.get("server_id"))
                channel_id = str(message.get("channel_id"))
                msg_id = str(message.get("message_id"))
                doc_ref = self.db.collection(collection_name)\
                    .document(server_id)\
                    .collection(channel_id)\
                    .document(msg_id)
                batch.set(doc_ref, message)
            batch.commit()

    def find_messages(self, collection_name: str, filters: Optional[List] = None):
        col_ref = self.db.collection(collection_name)
        if filters:
            for f in filters:
                col_ref = col_ref.where(*f)
        return [doc.to_dict() for doc in col_ref.stream()]

    @classmethod
    def get_instance(cls, cred_path: Optional[str] = None):
        return cls(cred_path)
