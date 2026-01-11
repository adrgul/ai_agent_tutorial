FROM python:3.11-slim

WORKDIR /app

# Python függőségek telepítése
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Alkalmazás másolása
COPY chat.py .

# Környezeti változók
ENV PYTHONUNBUFFERED=1

# Interaktív mód engedélyezése
CMD ["python", "-u", "chat.py"]

