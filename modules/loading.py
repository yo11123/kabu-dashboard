"""
DNA ヘリックス風ローディング UI
st.spinner の代わりに使用する。
"""
import streamlit as st
import streamlit.components.v1 as components

_CSS = """
<style>
.helix-loader {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 28px 0;
}
.helix-dots {
    display: flex;
    gap: 7px;
    align-items: center;
    height: 28px;
}
.helix-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #d4af37;
    animation: helixWave 2s ease-in-out infinite;
}
.helix-dot:nth-child(1)  { animation-delay: 0s; }
.helix-dot:nth-child(2)  { animation-delay: 0.12s; }
.helix-dot:nth-child(3)  { animation-delay: 0.24s; }
.helix-dot:nth-child(4)  { animation-delay: 0.36s; }
.helix-dot:nth-child(5)  { animation-delay: 0.48s; }
.helix-dot:nth-child(6)  { animation-delay: 0.6s; }
.helix-dot:nth-child(7)  { animation-delay: 0.72s; }
.helix-dot:nth-child(8)  { animation-delay: 0.84s; }
.helix-dot:nth-child(9)  { animation-delay: 0.96s; }
.helix-dot:nth-child(10) { animation-delay: 1.08s; }
.helix-dot:nth-child(11) { animation-delay: 1.2s; }
.helix-dot:nth-child(12) { animation-delay: 1.32s; }
@keyframes helixWave {
    0%, 100% { transform: translateY(8px); opacity: 0.25; background: #8fb8a0; }
    50% { transform: translateY(-8px); opacity: 1; background: #d4af37; }
}
.helix-text {
    font-family: 'Inter', 'Noto Sans JP', sans-serif;
    font-size: 0.82rem;
    color: #b8b0a2;
    letter-spacing: 0.03em;
}
</style>
"""

_DOTS = "".join('<div class="helix-dot"></div>' for _ in range(12))


def show_loading(message: str = "読み込み中...") -> None:
    """DNA ヘリックス風ローディングを表示する（単発表示用）。"""
    st.markdown(
        f'{_CSS}'
        f'<div class="helix-loader">'
        f'<div class="helix-dots">{_DOTS}</div>'
        f'<div class="helix-text">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


class helix_spinner:
    """
    st.spinner の代替。DNA ヘリックス風ローディングを表示する。

    使い方:
        with helix_spinner("分析中..."):
            heavy_function()
    """

    def __init__(self, message: str = "読み込み中..."):
        self.message = message
        self.placeholder = None

    def __enter__(self):
        self.placeholder = st.empty()
        self.placeholder.markdown(
            f'{_CSS}'
            f'<div class="helix-loader">'
            f'<div class="helix-dots">{_DOTS}</div>'
            f'<div class="helix-text">{self.message}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return self

    def __exit__(self, *args):
        if self.placeholder:
            self.placeholder.empty()
