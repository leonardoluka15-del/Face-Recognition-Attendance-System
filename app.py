import hmac
import io
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from storage import Store
from vision import FaceEngine

st.set_page_config(page_title='FacePass | Attendance', page_icon='📷', layout='wide')
st.markdown('''<style>.stApp{background:#0b1120} [data-testid="stMetric"]{background:#172238;padding:22px;border-radius:14px;border:1px solid #29374f} h1{letter-spacing:-1.5px} [data-testid="stSidebar"]{background:#101a2d}</style>''', unsafe_allow_html=True)

def secret(key):
    value = os.environ.get(key)
    if value: return value
    try: return st.secrets.get(key, '')
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError): return ''

password = secret('ADMIN_PASSWORD')
if not password:
    st.title('📷 FacePass')
    st.info('Set ADMIN_PASSWORD in your host secrets or environment, then restart the app. See README for setup.')
    st.stop()
if not st.session_state.get('authenticated'):
    st.title('📷 FacePass')
    st.caption('Attendance workspace • Administrator sign in')
    with st.form('login'):
        supplied = st.text_input('Administrator password', type='password')
        submit = st.form_submit_button('Sign in', type='primary')
    if submit:
        if hmac.compare_digest(supplied, password):
            st.session_state.authenticated = True
            st.rerun()
        else: st.error('Incorrect password.')
    st.stop()

store = Store(os.environ.get('ATTENDANCE_DB', 'private/attendance.db'))
engine = FaceEngine()
with st.sidebar:
    st.title('📷 FacePass')
    st.caption('RECOGNITION • ATTENDANCE')
    page = st.radio('Workspace', ['Overview', 'Enrol people', 'Camera attendance', 'People', 'Reports'])
    timezone = st.selectbox('Attendance timezone', ['Europe/Paris','Africa/Lagos','UTC'])
    st.caption('Prototype v0.1 • CPU recognition')
    if st.button('Sign out'):
        st.session_state.clear()
        st.rerun()
today = datetime.now(ZoneInfo(timezone)).date()
people = store.people()
st.title(page)
st.caption(f'{today:%A, %d %B %Y} · {timezone}')

if page == 'Overview':
    records = store.records(today,today)
    a,b,c = st.columns(3)
    a.metric('Registered people',len(people))
    b.metric('Checked in today',len(records))
    c.metric('Still present',sum(r['departure'] is None for r in records))
    st.subheader('Today’s activity')
    if records: st.dataframe(pd.DataFrame(records), hide_index=True, width='stretch')
    else: st.info('No attendance yet. Enrol a person, then open Camera attendance.')
    st.subheader('Attendance over the last 14 days')
    history = pd.DataFrame(store.records(today-timedelta(days=13),today))
    if not history.empty:
        counts = history.groupby('day').size()
        counts.index = pd.to_datetime(counts.index)
        st.bar_chart(counts.reindex(pd.date_range(today-timedelta(days=13),today),fill_value=0))

elif page == 'Enrol people':
    st.write('Capture at least three different, clear views of one consenting person. Keep the face mostly frontal.')
    code = st.text_input('Person ID', max_chars=60)
    name = st.text_input('Full name', max_chars=100)
    department = st.text_input('Department', max_chars=100)
    consent = st.checkbox('This person agrees to enrolment and storage of their face samples for this attendance prototype.')
    # A new ID cannot accidentally inherit another person’s staged samples.
    if st.session_state.get('sample_owner') != code:
        st.session_state.sample_owner = code
        st.session_state.staged = []
    staged = st.session_state.setdefault('staged',[])
    photo = st.camera_input('Take an enrolment photo')
    if st.button('Add this sample', disabled=photo is None or not consent):
        try:
            encoded = engine.encode(engine.extract(photo.getvalue()))
            if encoded in staged: st.warning('This sample is already added. Take another photo.')
            elif len(staged)>=10: st.warning('Maximum ten samples.')
            else: staged.append(encoded)
        except ValueError as e: st.error(str(e))
    st.caption(f'{len(staged)} / 3 minimum samples collected')
    if staged: st.image(staged, width=100)
    if st.button('Save person', type='primary', disabled=len(staged)<3 or not consent):
        try:
            store.enroll(code,name,department,staged,consent)
            st.session_state.staged=[]
            st.success('Person enrolled. Open Camera attendance to check in.')
        except (ValueError,sqlite3.IntegrityError) as e:
            st.error('Person ID already exists.' if isinstance(e,sqlite3.IntegrityError) else str(e))
    if st.button('Clear staged samples'):
        st.session_state.staged=[]
        st.rerun()

elif page == 'Camera attendance':
    st.info('Snapshot recognition prototype. Liveness detection is not implemented; photographs may fool it. Review matches before recording.')
    action = st.radio('Action',['Check in','Check out'],horizontal=True)
    photo = st.camera_input('Look at the camera and capture')
    threshold = st.slider('Maximum LBPH distance (lower is stricter)',30,80,55)
    if st.button('Recognise face',type='primary',disabled=photo is None):
        st.session_state.pop('candidate',None)
        try:
            pid,distance = engine.recognize(engine.extract(photo.getvalue()),store.samples(),threshold)
            if pid is None: st.warning(f'Unknown or ambiguous face (distance {distance:.1f}). No attendance recorded.')
            else: st.session_state.candidate=(pid,distance,photo.getvalue())
        except ValueError as e: st.error(str(e))
    candidate = st.session_state.get('candidate')
    if candidate and photo and candidate[2] == photo.getvalue():
        person = next((p for p in people if p['id']==candidate[0]),None)
        if person:
            st.success(f"Proposed match: {person['name']} · {person['code']} | distance {candidate[1]:.1f}")
            if st.button(f'Confirm {action.lower()}'):
                st.success(store.mark(person['id'],action,timezone))
                st.session_state.pop('candidate',None)
    with st.expander('Manual attendance alternative'):
        if people:
            selected = st.selectbox('Person',people,format_func=lambda p:f"{p['code']} — {p['name']}")
            if st.button('Record manually'): st.success(store.mark(selected['id'],action,timezone,method='manual'))

elif page == 'People':
    if not people: st.info('No registered people yet.')
    else:
        st.dataframe(pd.DataFrame(people)[['code','name','department','samples']],hide_index=True,width='stretch')
        selected = st.selectbox('Manage person',people,format_func=lambda p:f"{p['code']} — {p['name']}")
        confirm = st.checkbox('Delete this person, their face samples, and their attendance records permanently.')
        if st.button('Delete person',disabled=not confirm):
            store.delete(selected['id'])
            st.session_state.pop('candidate',None)
            st.rerun()

elif page == 'Reports':
    a,b = st.columns(2)
    start = a.date_input('Start date',today-timedelta(days=30))
    end = b.date_input('End date',today)
    if start>end: st.error('Start date must be before end date.')
    else:
        df = pd.DataFrame(store.records(start,end),columns=['code','name','department','day','arrival','departure','method'])
        st.dataframe(df,hide_index=True,width='stretch')
        # Neutralize spreadsheet formulas in user-entered text.
        safe = df.map(lambda v: "'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v)
        st.download_button('Download CSV',safe.to_csv(index=False).encode(),file_name='attendance.csv',mime='text/csv')
        buf=io.BytesIO()
        with pd.ExcelWriter(buf,engine='openpyxl') as writer: safe.to_excel(writer,index=False,sheet_name='Attendance')
        st.download_button('Download Excel',buf.getvalue(),file_name='attendance.xlsx')
