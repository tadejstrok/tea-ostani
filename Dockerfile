# Static petition site: plain HTML + assets served by nginx. No build step.
FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY public /usr/share/nginx/html/public
COPY nginx.conf /etc/nginx/conf.d/default.conf
