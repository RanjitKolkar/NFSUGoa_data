import streamlit as st
import pandas as pd
import os
import random
from collections import defaultdict
from io import BytesIO
import plotly.express as px

# === CONFIG ===
DATA_FOLDER = "Data"
HOUSE_COLORS = {
    "House A": "#FF9999",
    "House B": "#99CCFF",
    "House C": "#99FF99",
    "House D": "#FFCC99",
}


# === DATA LOADING ===
def load_all_students_from_data_folder():
    all_data = pd.DataFrame()
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith(".xlsx"):
            file_path = os.path.join(DATA_FOLDER, filename)
            df = pd.read_excel(file_path, header=2)

            df.columns = (
                df.columns.astype(str)
                .str.strip()
                .str.replace("\xa0", " ", regex=False)
                .str.replace(r"[\n\r\t]+", " ", regex=True)
                .str.replace(r"\s+", " ", regex=True)
            )

            df["Stream"] = os.path.splitext(filename)[0]
            all_data = pd.concat([all_data, df], ignore_index=True)
    return all_data


# === HOUSE ASSIGNMENT ===
def assign_houses(df, global_house_counts):
    assigned_df = df.copy()
    assigned_df["House"] = None
    for (stream, sem, gender), group_df in df.groupby(["Stream", "Semester", "Gender"]):
        students = group_df.index.tolist()
        random.shuffle(students)
        house_order = sorted(HOUSE_COLORS.keys(), key=lambda h: global_house_counts[gender][h])
        house_cycle = house_order * ((len(students) // 4) + 1)
        for i, idx in enumerate(students):
            house = house_cycle[i % 4]
            assigned_df.at[idx, "House"] = house
            global_house_counts[gender][house] += 1
    return assigned_df


# === HOUSE EXCEL DOWNLOAD ===
def get_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        display_cols = ["Enrollment No", "Student Name", "Gender", "Stream", "Semester", "House"]
        for stream in sorted(df["Stream"].unique()):
            for gender in ["M", "F"]:
                gender_df = df[(df["Stream"] == stream) & (df["Gender"] == gender)]
                if gender_df.empty:
                    continue
                export_df = gender_df[display_cols].sort_values("House")
                sheet_name = f"{stream[:25]}-{gender[:5]}"
                export_df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


# === STYLING ===
def highlight_house(house):
    color = HOUSE_COLORS.get(house, "#FFFFFF")
    return f"background-color: {color};"


# === VIEW DATA PAGE ===
def view_data_page(df):
    st.subheader("📂 View Student Data")

    streams = sorted(df["Stream"].unique())
    semesters = sorted(df["Semester"].unique())

    selected_streams = st.sidebar.multiselect("🎓 Filter by Stream", streams, default=streams)
    selected_sems = st.sidebar.multiselect("📘 Filter by Semester", semesters, default=semesters)
    selected_gender = st.sidebar.multiselect("⚧️ Filter by Gender", ["M", "F"], default=["M", "F"])

    all_columns = df.columns.tolist()
    default_cols = ["Enrollment No", "Student Name","Email-ID"]
    

    selected_cols = st.sidebar.multiselect("📋 Select Columns to Display", all_columns, default=default_cols)

    filtered = df.copy()
    if selected_streams:
        filtered = filtered[filtered["Stream"].isin(selected_streams)]
    if selected_sems:
        filtered = filtered[filtered["Semester"].isin(selected_sems)]
    if selected_gender:
        filtered = filtered[filtered["Gender"].isin(selected_gender)]

    st.dataframe(filtered[selected_cols], use_container_width=True)


# === HOUSE DISTRIBUTION PAGE ===
def house_distribution_page(df):
    st.subheader("🏠 House Distribution")
    global_house_counts = {"M": defaultdict(int), "F": defaultdict(int)}
    assigned_df = assign_houses(df, global_house_counts)

    st.download_button(
        label="📥 Download House Distribution Excel",
        data=get_excel_download(assigned_df),
        file_name="final_house_distribution.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    selected_streams = st.sidebar.multiselect("🎓 Filter by Stream", sorted(df["Stream"].unique()))
    selected_sems = st.sidebar.multiselect("📘 Filter by Semester", sorted(df["Semester"].unique()))
    selected_gender = st.sidebar.multiselect("⚧️ Filter by Gender", ["M", "F"], default=["M", "F"])

    display_cols = ["Enrollment No", "Student Name", "Gender", "Stream", "Semester", "House"]
    filtered_df = assigned_df.copy()
    if selected_streams:
        filtered_df = filtered_df[filtered_df["Stream"].isin(selected_streams)]
    if selected_sems:
        filtered_df = filtered_df[filtered_df["Semester"].isin(selected_sems)]
    if selected_gender:
        filtered_df = filtered_df[filtered_df["Gender"].isin(selected_gender)]

    styled_df = filtered_df[display_cols].sort_values("House").style.applymap(highlight_house, subset=["House"])
    st.dataframe(styled_df, use_container_width=True)

    st.markdown("### 📊 House Stats by Gender")
    for gender in ["M", "F"]:
        gender_df = assigned_df[assigned_df["Gender"] == gender]
        if not gender_df.empty:
            st.markdown(f"#### Gender: `{gender}`")
            counts = gender_df["House"].value_counts().reindex(HOUSE_COLORS.keys(), fill_value=0)
            st.write(pd.DataFrame({"House": counts.index, "Count": counts.values}))


# === VISUALIZATION PAGE ===
def visualize_page(df):
    st.subheader("📈 House Distribution Visualization")

    if "House" not in df.columns:
        st.warning("House distribution not found. Please visit the 'House Distribution' page first.")
        return

    stream_options = sorted(df["Stream"].unique())
    selected_streams = st.multiselect("🎓 Select Stream(s)", stream_options, default=stream_options)

    gender_filter = st.selectbox("⚧️ Filter by Gender", ["All", "M", "F"], index=0)

    viz_df = df.copy()
    if gender_filter != "All":
        viz_df = viz_df[viz_df["Gender"] == gender_filter]
    if selected_streams:
        viz_df = viz_df[viz_df["Stream"].isin(selected_streams)]

    if viz_df.empty:
        st.warning("No data available for selected filters.")
        return

    st.markdown("### 📊 Grouped Bar: House Count per Stream")
    fig1 = px.histogram(
        viz_df,
        x="Stream",
        color="House",
        barmode="group",
        title="House Distribution by Stream",
        color_discrete_map=HOUSE_COLORS
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### 📊 Stacked Bar: Gender within Houses")
    fig2 = px.histogram(
        viz_df,
        x="House",
        color="Gender",
        barmode="stack",
        title="Gender Breakdown per House",
        color_discrete_map={"M": "#0074D9", "F": "#FF69B4"}
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 🧭 Pie Chart: Overall House Proportion")
    fig3 = px.pie(
        viz_df,
        names="House",
        title="Overall House Distribution",
        color="House",
        color_discrete_map=HOUSE_COLORS
    )
    st.plotly_chart(fig3, use_container_width=True)

# === MAIN APP ===
def main():
    st.set_page_config(page_title="NFSU Goa Data", layout="wide")
    st.title("🎓 NFSU Goa Data")

    if not os.path.exists(DATA_FOLDER):
        st.error(f"`{DATA_FOLDER}` folder not found. Please create it and add your Excel files.")
        return

    df = load_all_students_from_data_folder()

    required_cols = {"Enrollment No", "Stream", "Student Name", "Gender", "Semester"}
    if not required_cols.issubset(df.columns):
        st.error(f"Missing required columns. Required: {required_cols}")
        return

    # === SIDEBAR MENU ===
    menu = st.sidebar.radio("📋 Menu", ["House Distribution", "Visualize","View Data"])

    if menu == "House Distribution":
        house_distribution_page(df)
    elif menu == "Visualize":
        global_house_counts = {"M": defaultdict(int), "F": defaultdict(int)}
        assigned_df = assign_houses(df, global_house_counts)
        visualize_page(assigned_df)
    elif menu == "View Data":
        if not verify_password():
            st.warning("Access denied. Please enter the admin password in the sidebar to continue.")
            return
        view_data_page(df)
    

def verify_password():
    correct_password = "nfsu@123"
    password = st.sidebar.text_input("🔒 Enter Admin Password", type="password")
    if password == correct_password:
        return True
    elif password != "":
        st.sidebar.error("Incorrect password.")
    return False

if __name__ == "__main__":
    main()
