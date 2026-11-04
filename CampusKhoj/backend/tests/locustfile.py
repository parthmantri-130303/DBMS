import random

import os
from locust import HttpUser, between, task


class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Authenticate real Kondhwa student Aarav Sharma (PRN 1251150353)
        res = self.client.post("/api/v1/auth/login", json={
            "username": "1251150353",
            "password": "Student@123",
            "portal": "student"
        })
        if res.status_code == 200:
            token = res.json().get("token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(4)
    def browse_kondhwa_items(self):
        """Browses Kondhwa lost & found items."""
        self.client.get("/api/v1/campuses/1/lost", headers=self.headers)
        self.client.get("/api/v1/campuses/1/found", headers=self.headers)

    @task(2)
    def browse_bibwewadi_items(self):
        """Cross-campus read-only browsing."""
        self.client.get("/api/v1/campuses/2/lost", headers=self.headers)
        self.client.get("/api/v1/campuses/2/found", headers=self.headers)

    @task(2)
    def view_item_detail(self):
        """Inspects item detail with public timeline."""
        item_id = random.randint(1, 10)
        self.client.get(f"/api/v1/found/{item_id}", headers=self.headers)
        self.client.get(f"/api/v1/timeline/FOUND/{item_id}", headers=self.headers)

    @task(1)
    def check_notifications(self):
        """Polls unread notifications count."""
        self.client.get("/api/v1/notifications?limit=5", headers=self.headers)

class AdminUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        res = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": os.environ.get("KHOJ_TEST_STAFF_PASSWORD", "Staff@CampusKhoj2026!"),
            "portal": "admin"
        })
        if res.status_code == 200:
            token = res.json().get("token")
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

    @task(3)
    def view_dashboard(self):
        """Fetches consolidated dashboard KPIs and urgent claim queue."""
        self.client.get("/api/v1/admin/dashboard", headers=self.headers)

    @task(2)
    def review_claims_queue(self):
        """Checks pending and under review claims."""
        self.client.get("/api/v1/admin/claims?status=PENDING", headers=self.headers)

    @task(1)
    def inspect_audit_trail(self):
        """Inspects recent audit logs."""
        self.client.get("/api/v1/admin/audit-logs", headers=self.headers)

