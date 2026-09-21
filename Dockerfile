FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY seed.py ./
RUN python seed.py > seed.json
COPY --from=frontend /build/dist ./frontend/dist
RUN addgroup --system spaceport \
    && adduser --system --ingroup spaceport spaceport \
    && mkdir -p /app/backend/data \
    && chown -R spaceport:spaceport /app/backend/data
WORKDIR /app/backend
USER spaceport
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
CMD ["sh", "-c", "python seed.py /app/seed.json --if-empty && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
