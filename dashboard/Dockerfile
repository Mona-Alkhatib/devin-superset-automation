FROM python:3.12-slim
WORKDIR /app
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY dashboard/app.py .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
