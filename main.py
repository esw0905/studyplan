# ============================================================
# 과목별 시험 D-Day 및 맞춤형 공부 시간 배분기
# 실행 방법: streamlit run main.py
# ============================================================

# ---------- 1. 라이브러리 불러오기 ----------
import streamlit as st               # 웹 화면을 만들어 주는 라이브러리
import pandas as pd                  # 표(데이터프레임)를 다루는 라이브러리
import plotly.express as px          # 그래프를 그려 주는 라이브러리
from datetime import datetime, timedelta   # 날짜 계산용
from zoneinfo import ZoneInfo        # 한국 시간대를 쓰기 위한 도구

# ---------- 2. 기본 설정 ----------
st.set_page_config(page_title="공부 시간 배분기", page_icon="📚", layout="wide")


def get_today():
    """한국 시간 기준 오늘 날짜를 돌려준다.
    (스트림릿 서버는 외국 시간을 쓰는 경우가 많아서 한국 시간으로 맞춰 줌)"""
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


# ---------- 3. 핵심 기능 함수들 ----------
def calc_dday(exam_date, base_date):
    """시험 날짜와 기준 날짜의 차이(D-Day)를 계산한다.
    예) 시험이 3일 뒤면 3, 오늘이면 0"""
    return (exam_date - base_date).days


def dday_text(dday):
    """D-Day 숫자를 'D-3', 'D-Day' 같은 글자로 바꿔 준다."""
    if dday > 0:
        return f"D-{dday}"
    elif dday == 0:
        return "D-Day"
    else:
        return "종료"


def calc_priority(difficulty, weakness, dday):
    """우선순위 점수를 계산한다.
    점수 = (난이도 x 취약도) / max(D-Day, 1)
    - 어렵고, 자신 없고, 시험이 가까울수록 점수가 커진다.
    - max(dday, 1)을 쓰는 이유: D-Day가 0일 때 0으로 나누는 오류를 막기 위해서."""
    return (difficulty * weakness) / max(dday, 1)


def allocate_hours(subjects, total_hours, base_date):
    """하루 공부 시간을 과목별 점수 비율대로 나눠서 {과목명: 시간} 형태로 돌려준다.
    아직 시험이 안 끝난 과목(D-Day >= 0)만 계산에 넣는다."""
    # (1) 시험이 아직 안 끝난 과목만 골라낸다
    active = [s for s in subjects if calc_dday(s["exam_date"], base_date) >= 0]
    if not active:
        return {}

    # (2) 과목별 점수를 계산한다
    scores = {}
    for s in active:
        dday = calc_dday(s["exam_date"], base_date)
        scores[s["name"]] = calc_priority(s["difficulty"], s["weakness"], dday)

    # (3) 점수 합계가 0이면 나눗셈이 불가능하므로 똑같이 나눈다 (예외 처리)
    score_sum = sum(scores.values())
    if score_sum == 0:
        equal = total_hours / len(scores)
        return {name: equal for name in scores}

    # (4) 점수 비율만큼 시간을 나눈다
    return {name: total_hours * sc / score_sum for name, sc in scores.items()}


def build_schedule(subjects, total_hours, start_date):
    """오늘부터 마지막 시험일까지 '날짜별 과목별 공부 시간표'를 만든다."""
    last_exam = max(s["exam_date"] for s in subjects)
    rows = []
    day = start_date
    while day <= last_exam:                      # 마지막 시험일까지 하루씩 반복
        hours = allocate_hours(subjects, total_hours, day)
        row = {"날짜": day.strftime("%m/%d (%a)")}
        for s in subjects:                       # 과목 순서대로 칸을 채운다
            row[s["name"]] = round(hours.get(s["name"], 0), 1)
        rows.append(row)
        day += timedelta(days=1)                 # 다음 날로 이동
    return pd.DataFrame(rows)


def validate_subject(name, exam_date, today, subjects):
    """과목 입력값이 올바른지 검사한다. 문제가 있으면 안내 문장을, 없으면 None을 돌려준다."""
    name = name.strip()
    if name == "":
        return "과목명을 입력해 주세요."
    if any(s["name"] == name for s in subjects):
        return f"'{name}' 과목은 이미 등록되어 있어요."
    if exam_date < today:
        return "이미 지난 날짜예요. 오늘 이후 날짜를 선택해 주세요."
    return None


# ---------- 4. 상태 저장소 준비 ----------
# st.session_state: 화면이 새로고침되어도 값을 기억하는 저장 공간
if "subjects" not in st.session_state:
    st.session_state["subjects"] = []

today = get_today()
subjects = st.session_state["subjects"]

# ---------- 5. 화면 제목 ----------
st.title("📚 과목별 D-Day & 맞춤형 공부 시간 배분기")
st.caption(f"오늘 날짜: {today.strftime('%Y년 %m월 %d일')} (한국 시간 기준)")

# ---------- 6. 사이드바: 하루 공부 시간 입력 ----------
with st.sidebar:
    st.header("⚙️ 설정")
    total_hours = st.number_input(
        "하루 총 공부 가능 시간 (시간)",
        min_value=0.5, max_value=16.0, value=4.0, step=0.5,
    )
    st.markdown("---")
    st.markdown(
        "**배분 원리**\n\n"
        "점수 = 난이도 × 취약도 ÷ D-Day\n\n"
        "점수가 높은 과목에 더 많은 시간을 배정해요."
    )
    # 연습용 예시 데이터를 한 번에 넣는 버튼
    if st.button("예시 데이터 넣기"):
        st.session_state["subjects"] = [
            {"name": "수학", "exam_date": today + timedelta(days=7), "difficulty": 5, "weakness": 4},
            {"name": "영어", "exam_date": today + timedelta(days=10), "difficulty": 3, "weakness": 2},
            {"name": "정보", "exam_date": today + timedelta(days=14), "difficulty": 2, "weakness": 3},
        ]
        st.rerun()

# ---------- 7. 과목 추가 입력 폼 ----------
st.subheader("1️⃣ 과목 등록")
with st.form("add_form", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns(4)
    name = c1.text_input("과목명", placeholder="예: 수학")
    exam_date = c2.date_input(
        "시험 날짜", value=today + timedelta(days=7),
        min_value=today, max_value=today + timedelta(days=120),
    )
    difficulty = c3.slider("난이도 (1=쉬움 ~ 5=어려움)", 1, 5, 3)
    weakness = c4.slider("취약도 (1=자신있음 ~ 5=자신없음)", 1, 5, 3)
    submitted = st.form_submit_button("➕ 과목 추가")

if submitted:
    try:
        error = validate_subject(name, exam_date, today, subjects)
        if error:
            st.error(error)          # 입력이 잘못되면 빨간 안내창을 띄운다
        else:
            subjects.append({
                "name": name.strip(), "exam_date": exam_date,
                "difficulty": difficulty, "weakness": weakness,
            })
            st.success(f"'{name.strip()}' 과목을 추가했어요!")
            st.rerun()
    except Exception as e:           # 예상하지 못한 오류가 나도 프로그램이 멈추지 않게 함
        st.error(f"과목을 추가하는 중 오류가 발생했어요: {e}")

# ---------- 8. 등록된 과목 목록 + 삭제 ----------
if not subjects:
    st.info("아직 등록된 과목이 없어요. 위에서 과목을 추가하거나 사이드바의 '예시 데이터 넣기'를 눌러 보세요.")
    st.stop()                        # 과목이 없으면 여기서 화면 그리기를 멈춘다

st.subheader("2️⃣ 등록된 과목")
list_df = pd.DataFrame([
    {
        "과목": s["name"],
        "시험일": s["exam_date"].strftime("%Y-%m-%d"),
        "D-Day": dday_text(calc_dday(s["exam_date"], today)),
        "난이도": s["difficulty"],
        "취약도": s["weakness"],
    }
    for s in subjects
])
st.dataframe(list_df, use_container_width=True, hide_index=True)

d1, d2 = st.columns([3, 1])
del_name = d1.selectbox("삭제할 과목", [s["name"] for s in subjects], key="del_select")
if d2.button("🗑️ 삭제"):
    st.session_state["subjects"] = [s for s in subjects if s["name"] != del_name]
    st.rerun()

# ---------- 9. 결과 계산 및 출력 ----------
st.subheader("3️⃣ 오늘의 맞춤 공부 시간")
try:
    today_hours = allocate_hours(subjects, total_hours, today)

    # 이미 시험이 끝난 과목이 있으면 안내만 해 준다
    finished = [s["name"] for s in subjects if calc_dday(s["exam_date"], today) < 0]
    if finished:
        st.warning(f"시험이 끝난 과목은 계산에서 제외했어요: {', '.join(finished)}")

    if not today_hours:
        st.info("계산할 과목이 없어요. 시험 날짜가 남은 과목을 추가해 주세요.")
        st.stop()

    # 결과 표 만들기 (점수가 높은 순으로 정렬)
    result_rows = []
    for s in subjects:
        if s["name"] in today_hours:
            dday = calc_dday(s["exam_date"], today)
            h = today_hours[s["name"]]
            result_rows.append({
                "과목": s["name"],
                "D-Day": dday_text(dday),
                "우선순위 점수": round(calc_priority(s["difficulty"], s["weakness"], dday), 2),
                "배정 시간(시간)": round(h, 1),
                "배정 시간(분)": int(round(h * 60)),
            })
    result_df = pd.DataFrame(result_rows).sort_values("우선순위 점수", ascending=False)

    left, right = st.columns(2)
    left.dataframe(result_df, use_container_width=True, hide_index=True)

    # 원형 그래프로 시간 비율 보여주기
    fig = px.pie(result_df, names="과목", values="배정 시간(시간)", hole=0.4)
    right.plotly_chart(fig, use_container_width=True)

    # ---------- 10. 날짜별 전체 시간표 ----------
    st.subheader("4️⃣ 시험일까지 날짜별 시간표 (단위: 시간)")
    st.caption("시험이 끝난 과목은 다음 날부터 0시간으로 처리되고, 남은 과목에 시간이 다시 배분돼요.")
    schedule_df = build_schedule(subjects, total_hours, today)
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)

    # 표를 CSV 파일로 내려받기
    csv = schedule_df.to_csv(index=False).encode("utf-8-sig")   # utf-8-sig: 엑셀에서 한글 안 깨짐
    st.download_button("📥 시간표 CSV 다운로드", csv, "study_schedule.csv", "text/csv")

except Exception as e:
    # 어떤 이유로든 계산 중 오류가 나도 화면이 죽지 않고 안내만 보여 준다
    st.error(f"계산 중 오류가 발생했어요. 입력값을 다시 확인해 주세요. (오류 내용: {e})")
