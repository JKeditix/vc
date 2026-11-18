window.ViralCut = window.ViralCut || {};

window.ViralCut.api = {
    async _handle(res) {
        let data = null;
        try {
            data = await res.json();
        } catch (_e) {
            data = null;
        }
        if (!res.ok) {
            const msg = (data && (data.detail || data.message)) || `Request failed (${res.status})`;
            throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
        }
        return data;
    },

    async listProjects() {
        const res = await fetch('/api/projects');
        return this._handle(res);
    },

    async getTranscript(projectId) {
        const res = await fetch(`/api/projects/${projectId}/transcript`);
        return this._handle(res);
    },

    async createFromUrl(payload) {
        const fd = new FormData();
        fd.append('url', payload.url);
        fd.append('rights_confirmed', String(Boolean(payload.rightsConfirmed)));
        fd.append('target_clip_duration', String(payload.targetClipDuration));
        fd.append('max_clips', String(payload.maxClips));
        fd.append('aspect_ratio', payload.aspectRatio);
        fd.append('export_preset', payload.exportPreset);

        const res = await fetch('/api/projects/url', { method: 'POST', body: fd });
        return this._handle(res);
    },

    async createFromUpload(payload) {
        const fd = new FormData();
        fd.append('file', payload.file);
        fd.append('rights_confirmed', String(Boolean(payload.rightsConfirmed)));
        fd.append('target_clip_duration', String(payload.targetClipDuration));
        fd.append('max_clips', String(payload.maxClips));
        fd.append('aspect_ratio', payload.aspectRatio);
        fd.append('export_preset', payload.exportPreset);

        const res = await fetch('/api/projects/upload', { method: 'POST', body: fd });
        return this._handle(res);
    },

    async deleteProject(projectId) {
        const res = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
        return this._handle(res);
    },

    async retryProject(projectId) {
        const res = await fetch(`/api/projects/${projectId}/retry`, { method: 'POST' });
        return this._handle(res);
    },

    async renderClip(clipId, options) {
        const res = await fetch(`/api/clips/${clipId}/render`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(options),
        });
        return this._handle(res);
    },

    async getSettings() {
        const res = await fetch('/api/settings');
        return this._handle(res);
    },

    async updateSettings(payload) {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        return this._handle(res);
    },
};

window.ViralCut.formatTime = function formatTime(seconds) {
    const s = Math.max(0, Number(seconds || 0));
    const mins = Math.floor(s / 60);
    const secs = Math.floor(s % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};
