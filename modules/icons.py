"""
アニメーション付きSVGアイコン

st.markdown(..., unsafe_allow_html=True) で使用するインラインSVGを返す関数群。
CSSアニメーションは modules/styles.py でグローバル定義済み。
"""


def trend_up() -> str:
    """📈 の代替 — 緑トレンドライン（ドロー＋フェードアウト）"""
    return (
        '<span class="anim-icon">'
        '<svg width="18" height="14" viewBox="0 0 56 40" fill="none">'
        '<path d="M4 34L16 22L30 27L52 8" stroke="#3fb950" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity=".2"/>'
        '<path d="M4 34L16 22L30 27L52 8" stroke="#3fb950" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="80" stroke-dashoffset="80">'
        '<animate attributeName="stroke-dashoffset" values="80;0;0;0" keyTimes="0;0.35;0.5;1" dur="3.5s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.05;0.5;0.7;1" dur="3.5s" repeatCount="indefinite"/>'
        '</path>'
        '<path d="M4 34L16 22L30 27L52 8" stroke="#3fb950" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="80" stroke-dashoffset="80">'
        '<animate attributeName="stroke-dashoffset" values="80;0;0;0" keyTimes="0;0.35;0.5;1" dur="3.5s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0;.12;.12;0;0" keyTimes="0;0.05;0.5;0.7;1" dur="3.5s" repeatCount="indefinite"/>'
        '</path>'
        '</svg></span>'
    )


def trend_down() -> str:
    """📉 の代替 — 赤トレンドライン（ドロー＋フェードアウト）"""
    return (
        '<span class="anim-icon">'
        '<svg width="18" height="14" viewBox="0 0 56 40" fill="none">'
        '<path d="M4 8L16 20L30 14L52 34" stroke="#f47067" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity=".2"/>'
        '<path d="M4 8L16 20L30 14L52 34" stroke="#f47067" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="80" stroke-dashoffset="80">'
        '<animate attributeName="stroke-dashoffset" values="80;0;0;0" keyTimes="0;0.35;0.5;1" dur="3.5s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.05;0.5;0.7;1" dur="3.5s" repeatCount="indefinite"/>'
        '</path>'
        '<path d="M4 8L16 20L30 14L52 34" stroke="#f47067" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="80" stroke-dashoffset="80">'
        '<animate attributeName="stroke-dashoffset" values="80;0;0;0" keyTimes="0;0.35;0.5;1" dur="3.5s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0;.12;.12;0;0" keyTimes="0;0.05;0.5;0.7;1" dur="3.5s" repeatCount="indefinite"/>'
        '</path>'
        '</svg></span>'
    )


def check_glow(delay: float = 0) -> str:
    """✅ の代替 — 緑glow丸チェック"""
    d = f"animation-delay:{delay}s;" if delay else ""
    return (
        f'<span class="anim-icon" style="animation:glowG 2.5s ease-in-out infinite;{d}">'
        '<svg width="14" height="14" viewBox="0 0 20 20" fill="none">'
        '<circle cx="10" cy="10" r="8" fill="#3fb950" fill-opacity=".1" stroke="#3fb950" stroke-width="1"/>'
        '<path d="M6 10.5L9 13.5L14.5 7" stroke="#3fb950" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg></span>'
    )


def warn_glow(delay: float = 0) -> str:
    """⚠️ の代替 — 赤glow三角警告"""
    d = f"animation-delay:{delay}s;" if delay else ""
    return (
        f'<span class="anim-icon" style="animation:glowR 2s ease-in-out infinite;{d}">'
        '<svg width="14" height="14" viewBox="0 0 20 20" fill="none">'
        '<path d="M10 2L19 17H1Z" fill="#f47067" fill-opacity=".1" stroke="#f47067" stroke-width="1" stroke-linejoin="round"/>'
        '<line x1="10" y1="8" x2="10" y2="12" stroke="#f47067" stroke-width="1.5" stroke-linecap="round"/>'
        '<circle cx="10" cy="14.5" r=".8" fill="#f47067"/>'
        '</svg></span>'
    )


def target_hit() -> str:
    """🎯 の代替 — 的＋矢命中アニメ"""
    return (
        '<span class="anim-icon">'
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none">'
        '<circle cx="12" cy="12" r="9" stroke="#e3b341" stroke-width=".8" opacity=".3"/>'
        '<circle cx="12" cy="12" r="6" stroke="#e3b341" stroke-width=".8" opacity=".5"/>'
        '<circle cx="12" cy="12" r="3" fill="#e3b341" fill-opacity=".15" stroke="#e3b341" stroke-width=".8"/>'
        '<circle cx="12" cy="12" r="1" fill="#e3b341" opacity=".8"/>'
        '<g style="animation:arrowFly 2.5s ease-out infinite,arrowShake 2.5s ease-out infinite;transform-origin:12px 12px;">'
        '<line x1="12" y1="12" x2="20" y2="4" stroke="#e3b341" stroke-width="1.2" stroke-linecap="round"/>'
        '<path d="M17 4L20 4L20 7" stroke="#e3b341" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"/>'
        '</g>'
        '<circle cx="12" cy="12" fill="#e3b341" style="animation:ringHit 2.5s ease-out infinite"/>'
        '<circle cx="12" cy="12" fill="#e3b341" style="animation:ringHit2 2.5s ease-out infinite"/>'
        '</svg></span>'
    )


def chat_dots() -> str:
    """💬 の代替 — 吹き出し＋typing dots"""
    return (
        '<span class="anim-icon">'
        '<svg width="16" height="16" viewBox="0 0 20 20" fill="none">'
        '<rect x="2" y="3" width="16" height="11" rx="3" fill="#d2a8ff" fill-opacity=".12" stroke="#d2a8ff" stroke-width=".8"/>'
        '<path d="M6 14L9 17V14" fill="#d2a8ff" fill-opacity=".12" stroke="#d2a8ff" stroke-width=".8" stroke-linejoin="round"/>'
        '<circle cx="7" cy="8.5" r="1" fill="#d2a8ff" opacity=".5" style="animation:dotBounce1 1.2s ease-in-out infinite"/>'
        '<circle cx="10" cy="8.5" r="1" fill="#d2a8ff" opacity=".5" style="animation:dotBounce2 1.2s ease-in-out 0.2s infinite"/>'
        '<circle cx="13" cy="8.5" r="1" fill="#d2a8ff" opacity=".5" style="animation:dotBounce3 1.2s ease-in-out 0.4s infinite"/>'
        '</svg></span>'
    )


def robot_avatar(size: str = "sm") -> str:
    """ロボットアバター。size="sm"(28x32) or "lg"(36x40)"""
    if size == "lg":
        return (
            '<span class="anim-icon">'
            '<svg width="36" height="40" viewBox="0 0 36 40" fill="none">'
            '<g style="animation:floatBot 3s ease-in-out infinite">'
            '<line x1="18" y1="1" x2="18" y2="7" stroke="#8b949e" stroke-width="1.5" stroke-linecap="round"/>'
            '<circle cx="18" cy="1" r="2.5" fill="#d2a8ff" fill-opacity=".5" stroke="#d2a8ff" stroke-width=".8" class="robot-antenna" style="animation:antennaPulse 2s ease-in-out infinite"/>'
            '<rect x="4" y="7" width="28" height="22" rx="7" fill="#2d333b" stroke="#444c56" stroke-width="1"/>'
            '<rect x="6" y="9" width="24" height="18" rx="5" fill="#373e47"/>'
            '<circle cx="4" cy="16" r="2.5" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
            '<circle cx="4" cy="16" r="1" fill="#3fb950" opacity=".3" style="animation:earGlow 2s ease-in-out infinite"/>'
            '<circle cx="32" cy="16" r="2.5" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
            '<circle cx="32" cy="16" r="1" fill="#3fb950" opacity=".3" style="animation:earGlow 2s ease-in-out .5s infinite"/>'
            '<g style="animation:blink 4s ease-in-out infinite;transform-origin:13px 17px">'
            '<circle cx="13" cy="17" r="4" fill="#fff"/>'
            '<circle cx="13" cy="17" r="3" fill="#58a6ff"/>'
            '<g style="animation:pupilDrift 5s ease-in-out infinite"><circle cx="13" cy="17" r="1.2" fill="#0d1117"/></g>'
            '<circle cx="14" cy="16" r=".7" fill="#fff" opacity=".6"/>'
            '</g>'
            '<g style="animation:blink 4s ease-in-out .1s infinite;transform-origin:23px 17px">'
            '<circle cx="23" cy="17" r="4" fill="#fff"/>'
            '<circle cx="23" cy="17" r="3" fill="#58a6ff"/>'
            '<g style="animation:pupilDrift 5s ease-in-out infinite"><circle cx="23" cy="17" r="1.2" fill="#0d1117"/></g>'
            '<circle cx="24" cy="16" r=".7" fill="#fff" opacity=".6"/>'
            '</g>'
            '<ellipse cx="18" cy="24" rx="3" ry="1.2" fill="#2d333b" stroke="#444c56" stroke-width=".6" class="robot-mouth"/>'
            '<rect x="8" y="29" width="8" height="6" rx="3" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
            '<rect x="20" y="29" width="8" height="6" rx="3" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
            '<circle cx="12" cy="37" r="2" fill="#2d333b" stroke="#444c56" stroke-width=".5"/>'
            '<circle cx="24" cy="37" r="2" fill="#2d333b" stroke="#444c56" stroke-width=".5"/>'
            '</g></svg></span>'
        )
    # small
    return (
        '<span class="anim-icon">'
        '<svg width="28" height="32" viewBox="0 0 28 32" fill="none">'
        '<g style="animation:floatBot 3s ease-in-out infinite">'
        '<line x1="14" y1="1" x2="14" y2="6" stroke="#8b949e" stroke-width="1.2" stroke-linecap="round"/>'
        '<circle cx="14" cy="1" r="2" fill="#d2a8ff" fill-opacity=".5" stroke="#d2a8ff" stroke-width=".6" class="robot-antenna" style="animation:antennaPulse 2s ease-in-out infinite"/>'
        '<rect x="4" y="6" width="20" height="18" rx="6" fill="#2d333b" stroke="#444c56" stroke-width="1"/>'
        '<circle cx="4" cy="14" r="2" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
        '<circle cx="4" cy="14" r=".8" fill="#3fb950" opacity=".4" style="animation:earGlow 2s ease-in-out infinite"/>'
        '<circle cx="24" cy="14" r="2" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
        '<circle cx="24" cy="14" r=".8" fill="#3fb950" opacity=".4" style="animation:earGlow 2s ease-in-out .5s infinite"/>'
        '<g style="animation:blink 4s ease-in-out infinite;transform-origin:10.5px 14px">'
        '<circle cx="10.5" cy="14" r="3.5" fill="#fff"/>'
        '<circle cx="10.5" cy="14" r="2.5" fill="#58a6ff"/>'
        '<g style="animation:pupilDrift 5s ease-in-out infinite"><circle cx="10.5" cy="14" r="1" fill="#0d1117"/></g>'
        '<circle cx="11.5" cy="13" r=".6" fill="#fff" opacity=".6"/>'
        '</g>'
        '<g style="animation:blink 4s ease-in-out .1s infinite;transform-origin:17.5px 14px">'
        '<circle cx="17.5" cy="14" r="3.5" fill="#fff"/>'
        '<circle cx="17.5" cy="14" r="2.5" fill="#58a6ff"/>'
        '<g style="animation:pupilDrift 5s ease-in-out infinite"><circle cx="17.5" cy="14" r="1" fill="#0d1117"/></g>'
        '<circle cx="18.5" cy="13" r=".6" fill="#fff" opacity=".6"/>'
        '</g>'
        '<ellipse cx="14" cy="20" rx="2.5" ry="1" fill="#2d333b" stroke="#444c56" stroke-width=".6" class="robot-mouth"/>'
        '<line x1="8" y1="24" x2="8" y2="29" stroke="#444c56" stroke-width="1" stroke-linecap="round"/>'
        '<line x1="20" y1="24" x2="20" y2="29" stroke="#444c56" stroke-width="1" stroke-linecap="round"/>'
        '<circle cx="8" cy="29.5" r="1.5" fill="#2d333b" stroke="#444c56" stroke-width=".5"/>'
        '<circle cx="20" cy="29.5" r="1.5" fill="#2d333b" stroke="#444c56" stroke-width=".5"/>'
        '</g></svg></span>'
    )


def robot_chat_avatar(talking: bool = False) -> str:
    """チャット用小型ロボットアバター（24x28）。talking=True で口パク。"""
    talk_cls = ' talking' if talking else ''
    mouth_anim = ' style="animation:mouthTalk .3s ease-in-out infinite"' if talking else ''
    antenna_dur = '.5s' if talking else '2s'
    return (
        f'<span class="anim-icon chat-avatar-ai{talk_cls}">'
        '<svg width="24" height="28" viewBox="0 0 28 32" fill="none">'
        '<g style="animation:floatBot 3s ease-in-out infinite">'
        '<line x1="14" y1="1" x2="14" y2="6" stroke="#8b949e" stroke-width="1.2" stroke-linecap="round"/>'
        f'<circle cx="14" cy="1" r="2" fill="#d2a8ff" fill-opacity=".5" stroke="#d2a8ff" stroke-width=".6" style="animation:antennaPulse {antenna_dur} ease-in-out infinite"/>'
        '<rect x="4" y="6" width="20" height="18" rx="6" fill="#2d333b" stroke="#444c56" stroke-width="1"/>'
        '<circle cx="4" cy="14" r="2" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
        '<circle cx="4" cy="14" r=".8" fill="#3fb950" opacity=".4" style="animation:earGlow 2s ease-in-out infinite"/>'
        '<circle cx="24" cy="14" r="2" fill="#2d333b" stroke="#444c56" stroke-width=".6"/>'
        '<circle cx="24" cy="14" r=".8" fill="#3fb950" opacity=".4" style="animation:earGlow 2s ease-in-out .5s infinite"/>'
        '<g style="animation:blink 4s ease-in-out infinite;transform-origin:10.5px 14px">'
        '<circle cx="10.5" cy="14" r="3.5" fill="#fff"/>'
        '<circle cx="10.5" cy="14" r="2.5" fill="#58a6ff"/>'
        '<g style="animation:pupilDrift 5s ease-in-out infinite"><circle cx="10.5" cy="14" r="1" fill="#0d1117"/></g>'
        '<circle cx="11.5" cy="13" r=".6" fill="#fff" opacity=".6"/>'
        '</g>'
        '<g style="animation:blink 4s ease-in-out .1s infinite;transform-origin:17.5px 14px">'
        '<circle cx="17.5" cy="14" r="3.5" fill="#fff"/>'
        '<circle cx="17.5" cy="14" r="2.5" fill="#58a6ff"/>'
        '<g style="animation:pupilDrift 5s ease-in-out infinite"><circle cx="17.5" cy="14" r="1" fill="#0d1117"/></g>'
        '<circle cx="18.5" cy="13" r=".6" fill="#fff" opacity=".6"/>'
        '</g>'
        f'<ellipse cx="14" cy="20" rx="2.5" ry="1" fill="#2d333b" stroke="#444c56" stroke-width=".6"{mouth_anim}/>'
        '</g></svg></span>'
    )


def render_user_bubble(text: str, time_str: str = "") -> str:
    """ユーザーメッセージのバブルHTMLを返す。"""
    import html as _html
    escaped = _html.escape(text).replace("\n", "<br>")
    time_html = f'<div class="chat-time">{time_str}</div>' if time_str else ""
    return (
        f'<div class="chat-row-user">'
        f'<div class="chat-bubble-user">{escaped}{time_html}</div>'
        f'</div>'
    )


def render_ai_bubble(content: str, talking: bool = False) -> str:
    """AIメッセージのバブルHTMLを返す。contentはMarkdown変換済みHTMLを想定。"""
    avatar = robot_chat_avatar(talking=talking)
    return (
        f'<div class="chat-row-ai">'
        f'{avatar}'
        f'<div class="chat-bubble-ai">{content}</div>'
        f'</div>'
    )
