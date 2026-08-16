import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account


def get_bigquery_client():
    credentials = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"])
    )

    return bigquery.Client(
        credentials=credentials,
        project=st.secrets["gcp_service_account"]["project_id"],
    )