#!/usr/bin/env bash
# Comprobaciones del bloque 2A: levanta todo desde cero, prueba la API de stock y la reserva tras order.created, y lo apaga.
set -uo pipefail

# Se ejecuta siempre desde la raíz del proyecto
cd "$(dirname "$0")/.."

# URLs de las APIs, contadores de resultados y los pedidos que se crean en las pruebas
ORDERS=http://localhost:8001
STOCK=http://localhost:8002
PASSED=0
FAILED=0
ORDER_ID=""
FAILED_ORDER_ID=""

# Al salir, haya ido bien o mal, borra contenedores y datos
trap 'docker compose down -v > /dev/null 2>&1' EXIT

# Imprime OK o FALLO según si la condición (el resto de argumentos) se cumple, y lleva la cuenta
check() {
  local name=$1
  shift
  if "$@"; then
    echo "OK    $name"
    PASSED=$((PASSED + 1))
  else
    echo "FALLO $name"
    FAILED=$((FAILED + 1))
  fi
}

# Devuelve las unidades disponibles de un producto según la API de stock
available() {
  curl -s "$STOCK/stock/$1" | jq -r '.available // empty'
}

# Crea un pedido y devuelve su id
create_order() {
  curl -s -X POST "$ORDERS/orders" \
    -H 'Content-Type: application/json' \
    -d "{\"product_id\": \"$1\", \"quantity\": $2, \"amount\": 50}" | jq -r '.id // empty'
}

# Lee todos los mensajes del topic stock como «clave|valor»
stock_messages() {
  docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
    --bootstrap-server kafka:9092 --topic stock --from-beginning --timeout-ms 10000 \
    --property print.key=true --property key.separator='|' 2> /dev/null
}

# Arranca desde cero; si no levanta, no tiene sentido seguir
docker compose down -v > /dev/null 2>&1
if ! make up; then
  echo "FALLO make up: el sistema no ha arrancado"
  exit 1
fi
echo

# 1. /health de stock responde 200
status=$(curl -s -o /dev/null -w '%{http_code}' "$STOCK/health")
check "GET /health de stock responde 200 (recibido $status)" test "$status" = 200

# 2. El catálogo inicial está cargado
teclado=$(available teclado)
monitor=$(available monitor)
check "GET /stock/teclado devuelve 5 y /stock/monitor devuelve 1 (recibido $teclado y $monitor)" \
  test "$teclado" = 5 -a "$monitor" = 1

# 3. Un producto que no existe devuelve 404
status=$(curl -s -o /dev/null -w '%{http_code}' "$STOCK/stock/raton")
check "GET /stock/raton responde 404 (recibido $status)" test "$status" = 404

# 4. Un pedido de 2 teclados acaba descontando 2 unidades
ORDER_ID=$(create_order teclado 2)
for _ in $(seq 20); do
  teclado=$(available teclado)
  [ "$teclado" = 3 ] && break
  sleep 1
done
check "Tras pedir 2 teclados, GET /stock/teclado acaba en 3 (recibido $teclado)" test "$teclado" = 3

# 5. El evento stock.reserved del pedido está en el topic stock, con el order_id como clave
event_type=$(stock_messages | grep "^$ORDER_ID|" | head -n 1 | cut -d '|' -f 2- | jq -r '.event_type // empty')
check "stock.reserved en el topic stock con clave order_id (recibido '${event_type}')" \
  test -n "$ORDER_ID" -a "$event_type" = stock.reserved

# 6. El pedido sigue en pending: todavía no hay payments
order_status=$(curl -s "$ORDERS/orders/$ORDER_ID" | jq -r '.status // empty')
check "El pedido sigue en pending (recibido $order_status)" test "$order_status" = pending

# 7. Un pedido de 5 monitores no descuenta nada ni publica eventos; espera a que stock lo procese (reserva en failed)
FAILED_ORDER_ID=$(create_order monitor 5)
for _ in $(seq 20); do
  reservation=$(docker compose exec -T db-stock psql -U stock -d stock -tAc \
    "SELECT status FROM reservations WHERE order_id = '$FAILED_ORDER_ID'")
  [ "$reservation" = failed ] && break
  sleep 1
done
monitor=$(available monitor)
events=$(stock_messages | grep -c "^$FAILED_ORDER_ID|")
check "Tras pedir 5 monitores, monitor sigue en 1 y no hay eventos en stock (reserva $reservation, $monitor, eventos: $events)" \
  test -n "$FAILED_ORDER_ID" -a "$reservation" = failed -a "$monitor" = 1 -a "$events" = 0

# 8. Las outbox de orders y stock quedan vacías
for _ in $(seq 20); do
  orders_pending=$(docker compose exec -T db-orders psql -U orders -d orders -tAc "SELECT count(*) FROM outbox")
  stock_pending=$(docker compose exec -T db-stock psql -U stock -d stock -tAc "SELECT count(*) FROM outbox")
  [ "$orders_pending" = 0 ] && [ "$stock_pending" = 0 ] && break
  sleep 1
done
check "Las outbox de orders y stock quedan vacías (filas: $orders_pending y $stock_pending)" \
  test "$orders_pending" = 0 -a "$stock_pending" = 0

# Resumen: sale con error si alguna comprobación ha fallado
echo
echo "Resumen: $PASSED OK, $FAILED FALLO"
[ "$FAILED" -eq 0 ]
