import os
import random
import shutil
import subprocess
import tempfile

import streamlit as st
import sympy as sp

# ============================================================
# 基本設定
# ============================================================
st.set_page_config(page_title="數學教材工具箱", page_icon="📐", layout="wide")

x = sp.symbols("x")
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# 欄寬比例：先存成變數（tuple），避免複製時被誤判格式
EDITOR_RATIO = (2, 1)

DEFAULT_MD = r"""# 一元二次方程式練習

## 一、基本觀念

一元二次方程式的一般式為 $ax^2 + bx + c = 0$，其中 $a \neq 0$。

公式解為：

$$
x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
$$

判別式 $D = b^2 - 4ac$ 決定根的性質：

| 判別式 | 根的性質 |
| --- | --- |
| $D > 0$ | 兩相異實根 |
| $D = 0$ | 重根 |
| $D < 0$ | 無實根 |

## 二、練習題

1. 因式分解 $x^2 + 5x + 6$
2. 解方程式 $x^2 - 9 = 0$
3. 求 $2x^2 - 3x + 1 = 0$ 的兩根

---

**提示**：先觀察常數項的因數組合。
"""


# ============================================================
# 共用函式：Pandoc 轉檔
# ============================================================
@st.cache_data(show_spinner=False)
def markdown_to_docx(md_text: str) -> bytes:
    """寫入暫存檔 → 呼叫 Pandoc → 讀回 docx 位元組。相同內容會使用快取。"""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input.md")
        out = os.path.join(tmp, "output.docx")
        with open(src, "w", encoding="utf-8") as f:
            f.write(md_text)
        result = subprocess.run(
            ["pandoc", src, "-f", "markdown", "-t", "docx", "-o", out],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Pandoc 轉換失敗")
        with open(out, "rb") as f:
            return f.read()


def safe_filename(name: str, default: str = "document") -> str:
    """移除檔名中不合法的字元，並補上 .docx 副檔名。"""
    name = (name or "").strip() or default
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    if name.lower().endswith(".docx"):
        return name
    return name + ".docx"


# ============================================================
# 出題機函式
# ============================================================
def generate_questions(n):
    """先隨機選兩個根，再展開成題目，答案在出題時就已知。"""
    items = []
    for _ in range(n):
        r1 = random.randint(-9, 9)
        r2 = random.randint(-9, 9)
        expr = sp.expand((x - r1) * (x - r2))
        items.append((sp.latex(expr), sp.latex(sp.factor(expr))))
    return items


def build_markdown(items):
    q_lines = []
    a_lines = []
    for i, (e, fct) in enumerate(items, start=1):
        q_lines.append(f"{i}. 因式分解 ${e}$")
        a_lines.append(f"{i}. ${fct}$")
    q = "\n".join(q_lines)
    a = "\n".join(a_lines)
    return f"# 因式分解練習\n\n{q}\n\n# 參考答案\n\n{a}\n"


# ============================================================
# Callback：必須在 widget 建立前修改 session_state
# ============================================================
def send_quiz_to_editor():
    st.session_state.editor_md = st.session_state.quiz_md


def load_uploaded_file():
    f = st.session_state.get("md_upload")
    if f is not None:
        try:
            st.session_state.editor_md = f.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            st.session_state.upload_error = "檔案不是 UTF-8 編碼，請另存為 UTF-8 後再上傳。"


def reset_editor():
    st.session_state.editor_md = DEFAULT_MD


# ============================================================
# 初始化
# ============================================================
st.session_state.setdefault("editor_md", DEFAULT_MD)

st.title("📐 數學教材工具箱")

if shutil.which("pandoc") is None:
    st.error("伺服器找不到 Pandoc，請確認 packages.txt 已設定。")
    st.stop()

tab_quiz, tab_editor = st.tabs(["🎲 因式分解出題機", "📝 Markdown 轉 Word"])

# ============================================================
# 分頁一：因式分解出題機
# ============================================================
with tab_quiz:
    st.subheader("因式分解出題機")

    n = st.slider("題數", 5, 50, 10)

    if st.button("產生題目", type="primary"):
        st.session_state.quiz_md = build_markdown(generate_questions(n))

    if "quiz_md" in st.session_state:
        quiz_md = st.session_state.quiz_md

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Markdown 原始碼**")
            st.code(quiz_md, language="markdown")
        with col2:
            st.markdown("**預覽**")
            with st.container(height=450, border=True):
                st.markdown(quiz_md)

        b1, b2 = st.columns(2)
        with b1:
            try:
                st.download_button(
                    "⬇️ 下載 Word 試卷（公式可編輯）",
                    data=markdown_to_docx(quiz_md),
                    file_name="exam.docx",
                    mime=DOCX_MIME,
                    key="dl_quiz",
                    width="stretch",
                )
            except RuntimeError as e:
                st.error(f"轉檔失敗：{e}")
        with b2:
            st.button(
                "✏️ 送到 Markdown 編輯器修改",
                on_click=send_quiz_to_editor,
                width="stretch",
            )
        st.caption("按下「送到編輯器」後，請點上方「📝 Markdown 轉 Word」分頁繼續編輯。")

# ============================================================
# 分頁二：Markdown 轉 Word（支援數學公式）
# ============================================================
with tab_editor:
    st.subheader("Markdown 轉 Word（支援數學公式）")

    with st.expander("📂 上傳 .md 檔／重設內容"):
        st.file_uploader(
            "上傳 Markdown 檔案（會取代目前內容）",
            type=["md", "markdown", "txt"],
            key="md_upload",
            on_change=load_uploaded_file,
        )
        if "upload_error" in st.session_state:
            st.error(st.session_state.pop("upload_error"))
        st.button("↺ 恢復預設範例", on_click=reset_editor)

    col_in, col_out = st.columns(2)

    with col_in:
        st.markdown("**輸入區**")
        st.text_area(
            "Markdown 內容",
            key="editor_md",
            height=500,
            label_visibility="collapsed",
        )
        st.caption("輸入後按 Ctrl + Enter（Mac：⌘ + Enter）或點擊輸入框外，預覽即更新。")

    with col_out:
        st.markdown("**預覽區**")
        with st.container(height=500, border=True):
            st.markdown(st.session_state.editor_md)

    st.divider()

    md_text = st.session_state.editor_md
    c1, c2 = st.columns(EDITOR_RATIO, vertical_alignment="bottom")
    with c1:
        fname = st.text_input("Word 檔名", value="document")
    with c2:
        if md_text.strip():
            try:
                with st.spinner("轉換中…"):
                    docx_bytes = markdown_to_docx(md_text)
                st.download_button(
                    "⬇️ 轉成 Word 下載",
                    data=docx_bytes,
                    file_name=safe_filename(fname),
                    mime=DOCX_MIME,
                    key="dl_editor",
                    type="primary",
                    width="stretch",
                )
            except RuntimeError as e:
                st.error(f"轉檔失敗：{e}")
        else:
            st.info("請先在左側輸入內容")

    with st.expander("💡 數學公式語法提示"):
        st.markdown(
            r"""
- 行內公式：`$x^2 + 1$`，開頭的 `$` 後面與結尾的 `$` 前面**不能有空格**
- 區塊公式：`$$` 單獨一行，公式寫在中間
- 分數 `\frac{a}{b}`、根號 `\sqrt{x}`、上下標 `x^{2}`、`a_{n}`
- 不等號 `\neq`、`\leq`、`\geq`，正負號 `\pm`
"""
        )
