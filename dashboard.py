import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Бизнес табло", layout="wide")

# ============================================================
# 1. Зареждане на данните
# ============================================================
sales = pd.read_csv("data/dashboard_sales.csv")
reviews = pd.read_csv("data/dashboard_reviews.csv")
forecast = pd.read_csv("data/dashboard_forecast.csv")

sales["Date"] = pd.to_datetime(sales["Date"])
reviews["ReviewDate"] = pd.to_datetime(reviews["ReviewDate"])
forecast["Date"] = pd.to_datetime(forecast["Date"])

st.title("Онлайн магазин за техника")

# ============================================================
# 2. Филтри
# ============================================================
st.sidebar.header("Филтри")

start_date = st.sidebar.date_input("От дата", sales["Date"].min())
end_date = st.sidebar.date_input("До дата", sales["Date"].max())

all_categories = sorted(sales["Category"].unique())
categories = st.sidebar.multiselect("Категория продукт", all_categories, default=all_categories)

all_segments = sorted(sales["Segment"].unique())
segments = st.sidebar.multiselect("Клиентски сегмент", all_segments, default=all_segments)

df = sales[
    (sales["Date"] >= pd.Timestamp(start_date)) &
    (sales["Date"] <= pd.Timestamp(end_date)) &
    (sales["Category"].isin(categories)) &
    (sales["Segment"].isin(segments))
].copy()

df_reviews = reviews[
    (reviews["ReviewDate"] >= pd.Timestamp(start_date)) &
    (reviews["ReviewDate"] <= pd.Timestamp(end_date)) &
    (reviews["Category"].isin(categories)) &
    (reviews["Segment"].isin(segments))
].copy()

if len(df) == 0:
    st.warning("Няма продажби за избраните филтри.")
    st.stop()

# ============================================================
# 3. KPI показатели
# ============================================================
total_revenue = df["Revenue"].sum()
total_profit = df["Profit"].sum()
margin = total_profit / total_revenue * 100
total_orders = df["OrderID"].nunique()
total_customers = df["CustomerID"].nunique()
aov = total_revenue / total_orders

# ръст: втората половина на избрания период спрямо първата
middle_date = df["Date"].min() + (df["Date"].max() - df["Date"].min()) / 2
first_half = df[df["Date"] <= middle_date]["Revenue"].sum()
second_half = df[df["Date"] > middle_date]["Revenue"].sum()
growth = (second_half - first_half) / first_half * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Общи приходи", f"{total_revenue:,.0f} евро")
col2.metric("Обща печалба", f"{total_profit:,.0f} евро")
col3.metric("Марж на печалбата", f"{margin:.1f}%")
col4.metric("Ръст на приходите", f"{growth:.1f}%")

col1, col2, col3 = st.columns(3)
col1.metric("Брой поръчки", total_orders)
col2.metric("Клиенти", total_customers)
col3.metric("Средна стойност на поръчка", f"{aov:,.2f} евро")

st.caption("Ръстът сравнява втората половина на избрания период с първата.")

# ============================================================
# 4. Приходи във времето и по категория
# ============================================================
df["Month"] = df["Date"].dt.to_period("M").astype(str)
# имената на колоните стават надписи в легендата, затова са на български
bulgarian_names = {"Revenue": "Приход", "Profit": "Печалба"}

monthly_revenue = df.groupby("Month")[["Revenue", "Profit"]].sum().reset_index()
monthly_revenue = monthly_revenue.rename(columns=bulgarian_names)

category_revenue = df.groupby("Category")[["Revenue", "Profit"]].sum().reset_index()
category_revenue = category_revenue.rename(columns=bulgarian_names)

col1, col2 = st.columns(2)

fig = px.bar(
    monthly_revenue,
    x="Month", y=["Приход", "Печалба"],
    barmode="group",
    title="Месечни приходи и печалба",
    labels={"value": "Евро", "variable": "", "Month": "Месец"}
)
col1.plotly_chart(fig, width="stretch")

fig = px.bar(
    category_revenue,
    x="Category", y=["Приход", "Печалба"],
    barmode="group",
    title="Приходи и печалба по категория",
    labels={"value": "Евро", "variable": "", "Category": "Категория"}
)
col2.plotly_chart(fig, width="stretch")

# ============================================================
# 5. Продукти и клиентски сегменти
# ============================================================
product_revenue = (
    df.groupby("Product")["Revenue"].sum()
      .sort_values(ascending=False)
      .head(10)
      .reset_index()
)

segment_customers = df.groupby("Segment")["CustomerID"].nunique().reset_index()

col1, col2 = st.columns(2)

fig = px.bar(
    product_revenue,
    x="Revenue", y="Product",
    orientation="h",
    title="Топ 10 продукти по приход",
    labels={"Revenue": "Приход (евро)", "Product": "Продукт"}
)
col1.plotly_chart(fig, width="stretch")

fig = px.pie(
    segment_customers,
    names="Segment", values="CustomerID",
    title="Разпределение на клиентските сегменти"
)
col2.plotly_chart(fig, width="stretch")

# ============================================================
# 6. Sentiment на клиентските мнения
# ============================================================
col1, col2 = st.columns(2)

sentiment_names = {"Positive": "Положителни", "Negative": "Отрицателни", "Neutral": "Неутрални"}
sentiment_colors = {"Положителни": "green", "Отрицателни": "red", "Неутрални": "gray"}

if len(df_reviews) > 0:
    df_reviews["Мнение"] = df_reviews["sentiment"].map(sentiment_names)
    sentiment_counts = df_reviews["Мнение"].value_counts().reset_index()

    fig = px.pie(
        sentiment_counts,
        names="Мнение", values="count",
        color="Мнение", color_discrete_map=sentiment_colors,
        title="Sentiment на клиентските мнения"
    )
    col1.plotly_chart(fig, width="stretch")

    df_reviews["Month"] = df_reviews["ReviewDate"].dt.to_period("M").astype(str)
    monthly_sentiment = df_reviews.groupby(["Month", "Мнение"]).size().reset_index(name="Reviews")

    fig = px.line(
        monthly_sentiment,
        x="Month", y="Reviews", color="Мнение",
        color_discrete_map=sentiment_colors,
        title="Sentiment по месеци",
        labels={"Month": "Месец", "Reviews": "Брой мнения"},
        markers=True
    )
    col2.plotly_chart(fig, width="stretch")
else:
    st.info("Няма мнения за избраните филтри.")

# ============================================================
# 7. Реални и прогнозирани продажби
# ============================================================
last_months = forecast[forecast["Date"] >= "2026-07-01"]
last_months = last_months.rename(columns={"Actual": "Реални", "Linear Regression": "Линейна регресия"})

fig = px.line(
    last_months,
    x="Date", y=["Реални", "Линейна регресия", "LSTM"],
    title="Реални и прогнозирани дневни приходи",
    labels={"value": "Приход (евро)", "variable": "", "Date": "Дата"}
)
st.plotly_chart(fig, width="stretch")

st.caption("Прогнозата е за всички продажби от 1 септември 2026 и не зависи от филтрите.")
