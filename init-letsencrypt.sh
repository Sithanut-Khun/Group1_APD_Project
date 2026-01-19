#!/bin/bash

# Configuration
DOMAIN="pose.ams.cards"
EMAIL="sithanutkhun@gmail.com"  # Add a valid email for Let's Encrypt notifications
STAGING=0  # Set to 1 for testing, 0 for production

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Let's Encrypt SSL Certificate Setup ===${NC}\n"

# Check if domain is set
if [ "$DOMAIN" = "pose.ams.cards" ]; then
    echo -e "${RED}ERROR: Please edit this script and set your domain!${NC}"
    exit 1
fi

# Check if email is set
if [ "$EMAIL" = "sithanutkhun@gmail.com" ]; then
    echo -e "${RED}ERROR: Please edit this script and set your email!${NC}"
    exit 1
fi

# Create required directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p ./nginx
mkdir -p ./certbot/conf
mkdir -p ./certbot/www

# Create temporary nginx config for initial certificate request
echo -e "${YELLOW}Creating temporary nginx config...${NC}"
cat > ./nginx/nginx.conf <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    client_max_body_size 100M;
}
EOF

# Start nginx with temporary config
echo -e "${YELLOW}Starting nginx...${NC}"
docker compose up -d web

# Wait for nginx to start
echo -e "${YELLOW}Waiting for nginx to start...${NC}"
sleep 5

# Request certificate
echo -e "${YELLOW}Requesting SSL certificate from Let's Encrypt...${NC}"

if [ $STAGING -eq 1 ]; then
    echo -e "${YELLOW}Using staging server (testing mode)${NC}"
    STAGING_ARG="--staging"
else
    echo -e "${GREEN}Using production server${NC}"
    STAGING_ARG=""
fi

docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    $STAGING_ARG \
    -d $DOMAIN \
    -d www.$DOMAIN

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Certificate obtained successfully!${NC}\n"
    
    # Now create the HTTPS nginx config
    echo -e "${YELLOW}Creating HTTPS nginx config...${NC}"
    cat > ./nginx/nginx.conf <<EOF
# HTTP - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://api:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    client_max_body_size 100M;
}
EOF

    # Reload nginx with HTTPS config
    echo -e "${YELLOW}Reloading nginx with HTTPS configuration...${NC}"
    docker compose restart web
    
    echo -e "${GREEN}✓ HTTPS setup complete!${NC}"
    echo -e "${GREEN}Your site should now be accessible at: https://$DOMAIN${NC}\n"
    
    # Start certbot for auto-renewal
    echo -e "${YELLOW}Starting certbot for auto-renewal...${NC}"
    docker compose up -d certbot
    
    echo -e "${GREEN}✓ Auto-renewal configured!${NC}"
else
    echo -e "${RED}✗ Failed to obtain certificate${NC}"
    echo -e "${YELLOW}Check the errors above and try again${NC}"
    exit 1
fi