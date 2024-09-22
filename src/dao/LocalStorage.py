import os
from typing import Dict, List
import json


class Localstorage:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    @staticmethod
    def _sanitize_identifier(identifier: str) -> str:
        return identifier.replace(':', '_')

    def _get_collection_path(self, collection_name: str) -> str:
        collection_path = os.path.join(self.folder_path, collection_name)
        if not os.path.exists(collection_path):
            os.makedirs(collection_path)
        return collection_path

    def _get_file_path(self, collection_name: str, identifier: str) -> str:
        sanitized_identifier = self._sanitize_identifier(identifier)
        collection_path = self._get_collection_path(collection_name)
        return os.path.join(collection_path, f"{sanitized_identifier}.json")

    def add_one(self, collection_name: str, document: Dict):
        if 'Identifier' in document.keys():
            doc_id = document.get('Identifier')
        else:
            doc_id = document.get('jobId')
        if not doc_id:
            print("Document must have an 'Identifier' field.")
            return

        file_path = self._get_file_path(collection_name, doc_id)
        if os.path.exists(file_path):
            print(f"文件id {doc_id} 已存在！")
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, ensure_ascii=False, indent=4)

    def add_many(self, collection_name: str, documents: List[Dict]):
        for document in documents:
            self.add_one(collection_name, document)

    def find_one(self, collection_name: str, identifier: str | dict) -> Dict:
        if isinstance(identifier, dict):
            if 'Identifier' in identifier.keys():
                identifier = identifier.get('Identifier')
            else:
                identifier = identifier.get('jobId')
        file_path = self._get_file_path(collection_name, identifier)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def find_many(self, collection_name: str, identifiers: List[str] | dict) -> List[Dict]:
        if isinstance(identifiers, dict):
            identifiers = identifiers.get('Identifier')
        result = []
        for identifier in identifiers:
            document = self.find_one(collection_name, identifier)
            if document:
                result.append(document)
        return result

    def find_all(self, collection_name: str) -> List[Dict]:
        result = []
        collection_path = self._get_collection_path(collection_name)
        for file_name in os.listdir(collection_path):
            if file_name.endswith('.json'):
                with open(os.path.join(collection_path, file_name), 'r', encoding='utf-8') as f:
                    document = json.load(f)
                    result.append(document)
        return result

    def update_document(self, collection_name: str, identifier: str, update: Dict) -> int:
        file_path = self._get_file_path(collection_name, identifier)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                document = json.load(f)
            document.update(update)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, ensure_ascii=False, indent=4)
            return 1
        return 0

    def delete_document(self, collection_name: str, identifier: str) -> int:
        file_path = self._get_file_path(collection_name, identifier)
        if os.path.exists(file_path):
            os.remove(file_path)
            return 1
        return 0

    def delete_all_documents(self, collection_name: str) -> int:
        deleted_count = 0
        collection_path = self._get_collection_path(collection_name)
        for file_name in os.listdir(collection_path):
            if file_name.endswith('.json'):
                os.remove(os.path.join(collection_path, file_name))
                deleted_count += 1
        return deleted_count
