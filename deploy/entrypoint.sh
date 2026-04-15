#!/bin/bash
set -e

echo "=========================================="
echo " Museum Video Monitor — All-in-One Start"
echo "=========================================="

# ---- 1. Initialize MySQL if needed ----
if [ ! -d "/var/lib/mysql/mysql" ]; then
    echo "[1/4] Initializing MySQL..."
    mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql
    
    # Start MySQL temporarily to run init.sql
    mysqld --user=mysql --datadir=/var/lib/mysql &
    MYSQL_PID=$!
    
    # Wait for MySQL to be ready
    for i in $(seq 1 30); do
        if mysqladmin ping -h 127.0.0.1 --silent 2>/dev/null; then
            break
        fi
        echo "  Waiting for MySQL... ($i/30)"
        sleep 2
    done
    
    # Set root password and run init script
    mysql -u root <<-EOF
        ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_PASSWORD:-root}';
        CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY '${MYSQL_PASSWORD:-root}';
        GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
        FLUSH PRIVILEGES;
EOF
    
    # Run init.sql
    if [ -f /docker-entrypoint-initdb.d/init.sql ]; then
        echo "  Running init.sql..."
        mysql -u root -p"${MYSQL_PASSWORD:-root}" < /docker-entrypoint-initdb.d/init.sql
    fi
    
    # Stop temporary MySQL
    kill $MYSQL_PID
    wait $MYSQL_PID 2>/dev/null || true
    echo "  MySQL initialized."
else
    echo "[1/4] MySQL data exists, skipping init."
fi

# ---- 2. Ensure directories ----
echo "[2/4] Ensuring data directories..."
mkdir -p /var/lib/mysql /data/minio
mkdir -p /app/data/videos /app/data/frames /app/models /app/backend/data
mkdir -p /var/log/supervisor
chown -R mysql:mysql /var/lib/mysql

# ---- 3. Configure Nginx ----
echo "[3/4] Configuring Nginx..."
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
nginx -t

# ---- 4. Start all services ----
echo "=========================================="
echo " Frontend:  http://localhost"
echo " Backend:   http://localhost:8080"
echo " API Docs:  http://localhost:8080/docs"
echo " MinIO:     http://localhost:9001"
echo " MySQL:     localhost:3306"
echo "=========================================="
echo "[4/4] Launching supervisord..."

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/museum.conf
