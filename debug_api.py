#!/usr/bin/env python3
"""Debug script to test the Rise Gardens API directly."""
import sys
import json
import logging
import getpass

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

# Inline constants to avoid HA relative imports
AUTH0_DOMAIN = "rise-api-prod.auth0.com"
CLIENT_ID = "emZRRctislhPO5ghhbWsJi5DNbvl4yUt"
REALM = "Username-Password-Authentication"
GRANT_TYPE = "http://auth0.com/oauth/grant-type/password-realm"
SCOPE = "openid profile email offline_access"
API_BASE = "https://prod-api.risegds.com/v2"

import time
import requests

class RiseGardensAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.14.9",
            "platform": "android",
            "version": "3.3.16",
        }

    def authenticate(self):
        url = f"https://{AUTH0_DOMAIN}/oauth/token"
        payload = {
            "username": self.username,
            "password": self.password,
            "realm": REALM,
            "scope": SCOPE,
            "client_id": CLIENT_ID,
            "grant_type": GRANT_TYPE,
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "auth0-client": "eyJuYW1lIjoicmVhY3QtbmF0aXZlLWF1dGgwIiwidmVyc2lvbiI6IjIuMTEuMCJ9",
            "User-Agent": "okhttp/3.14.9",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"\n--- Auth response ({resp.status_code}) ---")
        print(json.dumps(resp.json(), indent=2))
        if resp.status_code == 200:
            data = resp.json()
            self.access_token = data["access_token"]
            self.refresh_token = data.get("refresh_token")
            self.token_expires_at = time.time() + data.get("expires_in", 36000)
            self.headers["authorization"] = f"Bearer {self.access_token}"
            return True
        return False

    def get(self, path, **params):
        url = f"{API_BASE}{path}"
        resp = requests.get(url, headers=self.headers, params=params or None, timeout=30)
        full_url = resp.url
        print(f"\n--- GET {full_url} ({resp.status_code}) ---")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
        return resp


if __name__ == "__main__":
    email = input("Email: ")
    password = getpass.getpass("Password: ")

    api = RiseGardensAPI(email, password)
    if not api.authenticate():
        print("Authentication failed.")
        sys.exit(1)

    list_resp = api.get("/gardens/list_v2")
    api.get("/gardens/gardens_device_data")

    # Auto-extract garden IDs from list response
    garden_ids = []
    if list_resp and list_resp.status_code == 200:
        gardens = list_resp.json().get("gardens", [])
        garden_ids = [(g["id"], g.get("name", "?")) for g in gardens]
        if garden_ids:
            print(f"\nFound gardens: {garden_ids}")

    ids_to_query = [str(gid) for gid, _ in garden_ids]
    if not ids_to_query:
        manual = input("\nNo gardens auto-detected. Enter a garden_id manually (or Enter to skip): ").strip()
        if manual:
            ids_to_query = [manual]

    for garden_id in ids_to_query:
        print(f"\n=== Garden ID: {garden_id} ===")

        # Explore potential plant/position endpoints
        print(f"\n--- Exploring plant/position endpoints for garden {garden_id} ---")
        api.get(f"/gardens/{garden_id}/plants")
        api.get(f"/gardens/{garden_id}/pods")
        api.get(f"/gardens/{garden_id}/slots")
        api.get(f"/gardens/{garden_id}/cells")
        api.get(f"/gardens/{garden_id}/trays")
        api.get(f"/gardens/{garden_id}")
        api.get("/plants", garden_id=garden_id)
        api.get("/pods", garden_id=garden_id)
