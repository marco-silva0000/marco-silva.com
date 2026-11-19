/**
 * Centralized Player Badges, Initials, Color Picker, and Chat Row Renderer
 */

const SHARED_PLAYER_PALETTE = [
  { id: "crimson", hex: "#ef4444", name: "Crimson Red" },
  { id: "orange", hex: "#f97316", name: "Coral Orange" },
  { id: "amber", hex: "#f59e0b", name: "Amber Gold" },
  { id: "emerald", hex: "#10b981", name: "Emerald Green" },
  { id: "teal", hex: "#14b8a6", name: "Teal" },
  { id: "cyan", hex: "#06b6d4", name: "Sky Cyan" },
  { id: "blue", hex: "#3b82f6", name: "Royal Blue" },
  { id: "indigo", hex: "#6366f1", name: "Indigo" },
  { id: "purple", hex: "#8b5cf6", name: "Purple" },
  { id: "pink", hex: "#ec4899", name: "Fuchsia Pink" },
  { id: "rose", hex: "#f43f5e", name: "Rose" },
  { id: "slate", hex: "#64748b", name: "Slate Gray" },
];

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getPlayerInitials(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function renderPlayerAvatarHtml(player, sizeClass = "player-avatar-sm", extraStyle = "") {
  if (!player) {
    return `<span class="player-avatar ${sizeClass}" style="background-color:#94a3b8; ${extraStyle}">?</span>`;
  }
  const color = player.color || "#3b82f6";
  const initials = player.initials || getPlayerInitials(player.name || "Player");
  const title = escapeHtml(player.name || "Player");
  return `<span class="player-avatar ${sizeClass}" style="background-color:${color}; ${extraStyle}" title="${title}">${escapeHtml(initials)}</span>`;
}

function renderPlayerPillBadgeHtml(player, sizeClass = "player-avatar-xs") {
  if (!player) return "";
  const avatar = renderPlayerAvatarHtml(player, sizeClass);
  const name = escapeHtml(player.name || "Player");
  return `<span class="player-pill-badge">${avatar}<span class="player-name">${name}</span></span>`;
}

/**
 * Render a chat/event row with avatar, author colored by player, and bubble.
 */
function renderChatRowHtml(event, playersMap = {}) {
  const authorName = event.author || "System";
  const isSystem = authorName === "System" || !event.author;
  const player = (!isSystem && playersMap) ? Object.values(playersMap).find(p => p.name === authorName) : null;
  const color = player ? (player.color || "#3b82f6") : (isSystem ? "#64748b" : "#3b82f6");
  const avatarHtml = isSystem
    ? `<span class="player-avatar player-avatar-xs" style="background-color:#64748b;" title="System">🔔</span>`
    : renderPlayerAvatarHtml(player || { name: authorName, color: color }, "player-avatar-xs");

  let timeStr = "";
  if (event.timestamp) {
    const d = new Date(event.timestamp * 1000);
    timeStr = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  return `
    <div class="chat-row">
      ${avatarHtml}
      <div class="chat-bubble ${isSystem ? 'system-bubble' : ''}">
        <div class="chat-meta">
          <span class="chat-author" style="color:${color};">${escapeHtml(authorName)}</span>
          ${timeStr ? `<span class="chat-time">${timeStr}</span>` : ""}
        </div>
        <div class="chat-text">${escapeHtml(event.text || "")}</div>
      </div>
    </div>
  `;
}

/**
 * Color picker controller for pre-game lobby and host mid-game changes.
 */
let currentColorPickerTargetPid = null;
let onColorPickerSelectedCallback = null;

function openColorPickerModal(targetPlayerId, currentColor, onSelectCallback) {
  currentColorPickerTargetPid = targetPlayerId;
  onColorPickerSelectedCallback = onSelectCallback;

  const modal = document.getElementById("modal-player-color-picker");
  const grid = document.getElementById("player-color-picker-grid");
  if (!modal || !grid) return;

  const activeHex = (currentColor || "").toLowerCase();
  grid.innerHTML = SHARED_PLAYER_PALETTE.map(c => {
    const isActive = c.hex.toLowerCase() === activeHex;
    return `
      <button type="button" 
        class="player-swatch-btn ${isActive ? 'active' : ''}" 
        style="background-color:${c.hex};" 
        onclick="selectPlayerColor('${c.hex}')" 
        title="${escapeHtml(c.name)}"
        aria-label="${escapeHtml(c.name)}">
        ${isActive ? '✓' : ''}
      </button>
    `;
  }).join("");

  modal.style.display = "flex";
}

function selectPlayerColor(hex) {
  if (typeof onColorPickerSelectedCallback === "function") {
    onColorPickerSelectedCallback(currentColorPickerTargetPid, hex);
  }
  closeColorPickerModal();
}

function closeColorPickerModal() {
  const modal = document.getElementById("modal-player-color-picker");
  if (modal) modal.style.display = "none";
  currentColorPickerTargetPid = null;
  onColorPickerSelectedCallback = null;
}

// Global modal keyboard accessibility & backdrop close
document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    closeColorPickerModal();
  }
});

document.addEventListener("click", function(e) {
  const modal = document.getElementById("modal-player-color-picker");
  if (modal && e.target === modal) {
    closeColorPickerModal();
  }
});
