# demo-app: CI/CD-конвейер GitLab → Harbor → Docker (Ansible) / Kubernetes

Учебный проект, показывающий полный путь доставки небольшого сервиса: от коммита до запущенного контейнера и наблюдаемости.

## Что внутри

| Каталог / файл | Назначение |
|---|---|
| `app/` | Flask-сервис: `/`, `/health`, `/metrics` (Prometheus) |
| `tests/` | pytest-тесты |
| `Dockerfile` | образ на `python:3.12-slim`, запуск через gunicorn не от root, HEALTHCHECK |
| `.gitlab-ci.yml` | lint → test → build (push в Harbor) → deploy (Ansible, вручную) |
| `ansible/deploy.yml` | установка Docker, вход в Harbor, pull образа, запуск контейнера, проверка `/health` |
| `k8s/` | Namespace, Deployment (2 реплики, probes, лимиты, securityContext), Service, Kustomize |
| `monitoring/` | job для Prometheus и правила алертов (сервис недоступен, высокий p95) |

## Схема

```
git push → GitLab CI: flake8/yamllint → pytest → docker build → push в Harbor
                                                         │
                          (ручной запуск) Ansible ───────┴──► VM: docker pull + run → /health
                          или kubectl apply -k k8s/  ───────► Kubernetes
                                                         Prometheus ◄── /metrics
```

## Запуск шаг за шагом

### 1. Локально
```bash
pip install -r requirements-dev.txt
pytest -q
cd app && gunicorn --bind 127.0.0.1:8080 app:app
curl localhost:8080/health
```

### 2. Harbor
Создайте проект (например `demo`) и robot-аккаунт с правами push/pull.

### 3. GitLab
Создайте проект, залейте код и добавьте переменные CI/CD (Settings → CI/CD → Variables):
`HARBOR_REGISTRY`, `HARBOR_PROJECT`, `HARBOR_USER`, `HARBOR_PASSWORD` (masked), `DEPLOY_HOST`, `DEPLOY_USER`, `SSH_PRIVATE_KEY`.
Для сборки нужен runner с поддержкой docker-in-docker (privileged).

### 4. Сервер для деплоя
Ubuntu/Debian-VM с SSH-доступом по ключу и sudo для пользователя `DEPLOY_USER`. Docker поставит playbook.
Если Harbor работает по HTTP или с самоподписанным сертификатом, добавьте его в `insecure-registries` или установите сертификат на VM.

### 5. Деплой
После успешной сборки в ветке `main` запустите вручную job `deploy`. Playbook можно запустить и локально:
```bash
cd ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory.ini deploy.yml \
  -e registry=harbor.example.com -e registry_project=demo \
  -e registry_user=robot\$ci -e registry_password=... -e image_tag=latest
```

### 6. Kubernetes (по желанию, например minikube или k3s)
```bash
kubectl create namespace demo
kubectl -n demo create secret docker-registry harbor-pull \
  --docker-server=harbor.example.com --docker-username=... --docker-password=...
cd k8s
kustomize edit set image harbor.example.com/demo/demo-app=<ваш реестр>/demo/demo-app:<тег>
kubectl apply -k .
kubectl -n demo rollout status deploy/demo-app
```

### 7. Мониторинг
Добавьте `monitoring/prometheus-scrape.yml` в конфиг Prometheus (подставьте адрес VM), подключите `alerts.yml` через `rule_files`, подключите Prometheus как источник данных в Grafana и постройте панели по `demo_app_requests_total` и `demo_app_request_seconds`.

## Принятые решения
- Образ тегируется коротким SHA коммита, поэтому любую версию можно воспроизвести и откатить. Тег `latest` нужен только для удобства.
- Деплой в продакшен запускается вручную (`when: manual`), чтобы выкатка была осознанным действием.
- Контейнер запускается не от root, K8s Deployment работает с read-only файловой системой.
- Пароль Harbor передаётся в Ansible как masked-переменная, в логах скрыт (`no_log`).

## Что можно улучшить дальше
Сканирование образа (Trivy) в pipeline, сборка через kaniko без privileged, Ansible Vault, Helm-чарт вместо Kustomize, автоматический деплой в K8s из GitLab, Ingress с TLS.
