# Customer Support MCP Server

Навчальний MCP-сервер для роботи із замовленнями, платежами, поверненнями та FAQ.

## Вимоги

- Python 3.10 або новіший;
- Node.js LTS із `npm` для запуску MCP Inspector.

Перевірити встановлені версії можна командами:

```bash
python --version
node --version
npm --version
```

> Якщо проєкт запускається у WSL, Node.js потрібно встановити безпосередньо
> всередині WSL. Команди `which node` і `which npm` не повинні повертати
> шляхи, що починаються з `/mnt/c/`.

## Запуск і тестування

Відкрийте термінал у корені проєкту.

Для автоматичної підготовки середовища, запуску тестів та MCP Inspector виконайте:

```bash
bash run_server_test.sh
```

Скрипт:

1. створить віртуальне середовище `.venv`;
2. активує його;
3. встановить залежності з `requirements.txt`;
4. запустить тести через `pytest`;
5. встановить Node.js-залежності з `package.json`;
6. запустить MCP Inspector.

Після запуску Inspector відкрийте URL, який він виведе в терміналі, якщо не було відкрито в браузері. Для завершення роботи натисніть `Ctrl+C`.

## Ручний запуск

Підготувати Python-середовище та запустити тести окремо:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest test_mcp_server.py -v
```

Встановити залежності Inspector:

```bash
npm install
```

Запустити MCP Inspector для сервера:

```bash
npm run inspector
```

Запустити сервер без Inspector:

```bash
source .venv/bin/activate
python mcp_server.py
```

## Можливості сервера

- перевірка статусу замовлення;
- перевірка платежу;
- оформлення повернення для доставленого замовлення;
- пошук інформації у FAQ;
- ресурс `support://info` із загальною інформацією про сервіс.
