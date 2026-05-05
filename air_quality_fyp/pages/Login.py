import streamlit as st

from src.auth import authenticate, create_user, login_as, logout, current_user
from src.ui_theme import apply_theme, render_page_header

st.set_page_config(page_title="Login", layout="centered")
apply_theme()

render_page_header("🔐 账户登录", "登录后将自动跳转到首页仪表盘。")


def _go_home() -> None:
    try:
        st.switch_page("app.py")
    except Exception:
        st.markdown("[➡️ 进入首页](/)")
        st.experimental_rerun()

user = current_user()
if user:
    st.success(f"已登录：{user.email}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("退出登录"):
            logout()
            st.experimental_rerun()
    with c2:
        if st.button("进入首页", type="primary"):
            _go_home()
    st.stop()

tab_login, tab_signup = st.tabs(["登录", "注册"])

with tab_login:
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("邮箱", placeholder="name@example.com")
        password = st.text_input("密码", type="password", placeholder="至少 8 位")
        submitted = st.form_submit_button("登录", type="primary")
    if submitted:
        ok, msg = authenticate(email, password)
        if ok:
            login_as(email)
            st.success(msg)
            _go_home()
        else:
            st.error(msg)

with tab_signup:
    with st.form("signup_form", clear_on_submit=False):
        email2 = st.text_input("邮箱（注册）", placeholder="name@example.com")
        pw1 = st.text_input("密码（注册）", type="password", placeholder="至少 8 位")
        pw2 = st.text_input("确认密码", type="password")
        signup_submitted = st.form_submit_button("注册")
    if signup_submitted:
        if pw1 != pw2:
            st.error("两次密码不一致。")
        else:
            ok, msg = create_user(email2, pw1)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
