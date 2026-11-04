/**
 * CampusKhoj API Client (Vanilla ES Module)
 * Handles token persistence, error normalization, and standard endpoints.
 */

const API_BASE = window.CAMPUSKHOJ_API_BASE || 'http://127.0.0.1:5000/api/v1';

export class ApiClient {
  constructor(portal = 'student') {
    this.portal = portal;
    this.storageKey = `campuskhoj_token_${portal}`;
    this.userKey = `campuskhoj_user_${portal}`;
  }

  getToken() {
    return sessionStorage.getItem(this.storageKey) || localStorage.getItem(this.storageKey);
  }

  setToken(token, user = null, remember = false) {
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem(this.storageKey, token);
    if (user) {
      storage.setItem(this.userKey, JSON.stringify(user));
    }
  }

  getUser() {
    const raw = sessionStorage.getItem(this.userKey) || localStorage.getItem(this.userKey);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  clearAuth() {
    sessionStorage.removeItem(this.storageKey);
    sessionStorage.removeItem(this.userKey);
    localStorage.removeItem(this.storageKey);
    localStorage.removeItem(this.userKey);
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  enforceStudentFlow() {
    if (!this.isAuthenticated()) {
      if (!window.location.pathname.includes('login')) {
        window.location.href = 'login.html';
        return false;
      }
      return true;
    }
    const user = this.getUser();
    if (user?.must_change_password) {
      if (!window.location.pathname.includes('change-password')) {
        window.location.href = 'change-password.html';
        return false;
      }
    } else if (this.portal === 'student' && user && !user.profile_completed) {
      if (!window.location.pathname.includes('profile-setup') && !window.location.pathname.includes('change-password') && !window.location.pathname.includes('login')) {
        window.location.href = 'profile-setup.html';
        return false;
      }
    }
    return true;
  }

  async fetch(endpoint, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    options.headers = headers;
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

    try {
      const response = await window.fetch(url, options);

      // Handle CSV stream
      if (options.asCsv) {
        if (!response.ok) throw new Error('Failed to export CSV');
        return await response.blob();
      }

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const error = data.error || {
          code: 'HTTP_ERROR',
          message: `Request failed with status ${response.status}`,
          details: {}
        };

        // Redirect on scope mismatch
        if (error.code === 'PASSWORD_CHANGE_REQUIRED') {
          if (!window.location.pathname.includes('change-password')) {
            window.location.href = 'change-password.html';
          }
        } else if (response.status === 401 && !window.location.pathname.includes('login')) {
          this.clearAuth();
          window.location.href = 'login.html';
        }

        const err = new Error(error.message);
        err.code = error.code;
        err.details = error.details;
        err.status = response.status;
        throw err;
      }

      return data;
    } catch (networkError) {
      if (networkError.code) throw networkError;
      const err = new Error('Could not connect to CampusKhoj server. Please ensure the backend is running.');
      err.code = 'NETWORK_ERROR';
      throw err;
    }
  }

  // --- Auth Endpoints ---
  async login(username, password) {
    const res = await this.fetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password, portal: this.portal })
    });
    if (res.user) {
      res.user.must_change_password = !!res.must_change_password;
      res.user.scope = res.scope;
    }
    this.setToken(res.token, res.user);
    return res;
  }

  async changePassword(currentPassword, newPassword) {
    const res = await this.fetch('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
    if (res.token) {
      this.setToken(res.token);
      try {
        const me = await this.getMe();
        if (me && me.user) {
          this.setToken(res.token, me.user);
        }
      } catch {}
    }
    return res;
  }

  async getMe() {
    return await this.fetch('/auth/me');
  }

  async logout() {
    try {
      await this.fetch('/auth/logout', { method: 'POST' });
    } finally {
      this.clearAuth();
    }
  }

  async updateProfile(profileData) {
    const res = await this.fetch('/me/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData)
    });
    try {
      const me = await this.getMe();
      if (me && me.user) {
        this.setToken(this.getToken(), me.user);
      }
    } catch {}
    return res;
  }

  // --- Reference & Items Endpoints ---
  async getCampuses() {
    return await this.fetch('/campuses');
  }

  async getCampusLocations(campusId) {
    return await this.fetch(`/campuses/${campusId}/locations`);
  }

  async getCategories() {
    return await this.fetch('/categories');
  }

  async getCampusLost(campusId, params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.fetch(`/campuses/${campusId}/lost?${query}`);
  }

  async getCampusFound(campusId, params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.fetch(`/campuses/${campusId}/found?${query}`);
  }

  async getLostDetail(lostId) {
    return await this.fetch(`/lost/${lostId}`);
  }

  async getFoundDetail(foundId) {
    return await this.fetch(`/found/${foundId}`);
  }

  async getRecentFoundItems(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.fetch(`/found/recent${query ? '?' + query : ''}`);
  }

  async searchFoundItems(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.fetch(`/found/search${query ? '?' + query : ''}`);
  }

  async requestDoubleVerification(foundId, data) {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    return await this.fetch(`/found/${foundId}/double-verify`, {
      method: 'POST',
      body: isFormData ? data : JSON.stringify(data)
    });
  }

  async reportLost(formData) {
    return await this.fetch('/lost', {
      method: 'POST',
      body: formData
    });
  }

  async reportFound(formData) {
    return await this.fetch('/found', {
      method: 'POST',
      body: formData
    });
  }

  async getMyLost() {
    return await this.fetch('/me/lost');
  }

  async getMyFound() {
    return await this.fetch('/me/found');
  }

  async getLostMatches(lostId) {
    return await this.fetch(`/lost/${lostId}/matches`);
  }

  async closeLost(lostId) {
    return await this.fetch(`/lost/${lostId}/close`, { method: 'POST' });
  }

  async closeFound(foundId) {
    return await this.fetch(`/found/${foundId}/close`, { method: 'POST' });
  }

  async getRecentItems(params = {}) {
    const query = new URLSearchParams(params).toString();
    return await this.fetch(`/items/recent?${query}`);
  }

  // --- Claims Endpoints ---
  async submitClaim(foundId, claimData, lostId = null) {
    let body;
    if (claimData instanceof FormData) {
      body = claimData;
    } else if (typeof claimData === 'string') {
      body = JSON.stringify({ claim_description: claimData, lost_id: lostId });
    } else {
      body = JSON.stringify(claimData);
    }
    return await this.fetch(`/found/${foundId}/claims`, {
      method: 'POST',
      body
    });
  }

  async getMyClaims() {
    return await this.fetch('/me/claims');
  }

  async getClaimDetail(claimId) {
    return await this.fetch(`/claims/${claimId}`);
  }

  async submitClaimAnswers(claimId, answers) {
    return await this.fetch(`/claims/${claimId}/answers`, {
      method: 'POST',
      body: JSON.stringify({ answers })
    });
  }

  async getClaimMessages(claimId) {
    return await this.fetch(`/claims/${claimId}/messages`);
  }

  async sendClaimMessage(claimId, message) {
    return await this.fetch(`/claims/${claimId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message })
    });
  }

  async cancelClaim(claimId) {
    return await this.fetch(`/claims/${claimId}/cancel`, { method: 'POST' });
  }

  async getClaimPassport(claimId) {
    return await this.fetch(`/claims/${claimId}/passport`);
  }

  async getItemPosterData(itemType, itemId) {
    return await this.fetch(`/items/${itemType}/${itemId}/poster-data`);
  }

  async verifyPassportCode(code) {
    return await this.fetch('/admin/claims/verify-passport', {
      method: 'POST',
      body: JSON.stringify({ code })
    });
  }

  // --- Timeline & Notifications ---
  async getTimeline(itemType, itemId) {
    return await this.fetch(`/items/${itemType}/${itemId}/timeline`);
  }

  async getNotifications() {
    return await this.fetch('/me/notifications');
  }

  async getUnreadNotificationCount() {
    return await this.fetch('/me/notifications/unread_count');
  }

  async markNotificationRead(notifId) {
    return await this.fetch(`/me/notifications/${notifId}/read`, { method: 'POST' });
  }

  async markAllNotificationsRead() {
    return await this.fetch('/me/notifications/read_all', { method: 'POST' });
  }

  // --- Simulated Message Outbox Endpoints ---
  async getMyMessages(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/me/messages${q ? '?' + q : ''}`);
  }

  async getMyMessagesUnreadCount() {
    return await this.fetch('/me/messages/unread_count');
  }

  async markAllMessagesRead() {
    return await this.fetch('/me/messages/read_all', { method: 'POST' });
  }

  async getAdminMessages(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/admin/messages${q ? '?' + q : ''}`);
  }

  // --- Admin Locations Management ---
  async getAdminLocations(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/admin/locations${q ? '?' + q : ''}`);
  }

  async addAdminLocation(data) {
    return await this.fetch('/admin/locations', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async updateAdminLocation(locId, data) {
    return await this.fetch(`/admin/locations/${locId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  async deleteAdminLocation(locId) {
    return await this.fetch(`/admin/locations/${locId}`, {
      method: 'DELETE'
    });
  }

  // --- Admin Endpoints ---
  async getAdminDashboard(campus = null) {
    const q = campus ? `?campus=${campus}` : '';
    return await this.fetch(`/admin/dashboard${q}`);
  }

  async getAdminItems(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/admin/items?${q}`);
  }

  async exportAdminItemsCsv(params = {}) {
    const p = { ...params, format: 'csv' };
    const q = new URLSearchParams(p).toString();
    return await this.fetch(`/admin/items?${q}`, { asCsv: true });
  }

  async getAdminItemDetail(itemType, itemId) {
    return await this.fetch(`/admin/items/${itemType}/${itemId}`);
  }

  async getAdminClaims(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/admin/claims?${q}`);
  }

  async startClaimReview(claimId) {
    return await this.fetch(`/admin/claims/${claimId}/start-review`, { method: 'POST' });
  }

  async addVerificationQuestion(claimId, question, expectedEvidence = null) {
    return await this.fetch(`/admin/claims/${claimId}/questions`, {
      method: 'POST',
      body: JSON.stringify({ question, expected_evidence: expectedEvidence })
    });
  }

  async verifyQuestionAnswer(claimId, verificationId, status) {
    return await this.fetch(`/admin/claims/${claimId}/verify`, {
      method: 'POST',
      body: JSON.stringify({ verification_id: verificationId, status })
    });
  }

  async approveClaim(claimId) {
    return await this.fetch(`/admin/claims/${claimId}/approve`, { method: 'POST' });
  }

  async rejectClaim(claimId, reason) {
    return await this.fetch(`/admin/claims/${claimId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    });
  }

  async recordHandover(claimId, receivedByPrn) {
    return await this.fetch(`/admin/claims/${claimId}/handover`, {
      method: 'POST',
      body: JSON.stringify({ received_by_prn: receivedByPrn })
    });
  }

  async getAdminUsers(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/admin/users?${q}`);
  }

  async toggleSuspendUser(userId) {
    return await this.fetch(`/admin/users/${userId}/suspend`, { method: 'POST' });
  }

  async resetUserPassword(userId) {
    return await this.fetch(`/admin/users/${userId}/reset-password`, { method: 'POST' });
  }

  async unlockUserAccount(userId) {
    return await this.fetch(`/admin/users/${userId}/unlock`, { method: 'POST' });
  }

  async importPrns(campusId, prns) {
    return await this.fetch('/admin/prn-registry/import', {
      method: 'POST',
      body: JSON.stringify({ campus_id: campusId, prns })
    });
  }

  async getAnalytics(metric) {
    return await this.fetch(`/admin/analytics/${metric}`);
  }

  async getAuditLogs(params = {}) {
    const q = new URLSearchParams(params).toString();
    return await this.fetch(`/admin/audit-logs?${q}`);
  }

  async getStaff() {
    return await this.fetch('/admin/staff');
  }

  async createStaff(staffData) {
    return await this.fetch('/admin/staff', {
      method: 'POST',
      body: JSON.stringify(staffData)
    });
  }
}
