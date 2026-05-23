FROM nginx:alpine

# Copy index.html as a template
COPY index.html /usr/share/nginx/html/index.template.html

# Default backend URL (can be overridden at runtime)
ENV BACKEND_URL=http://localhost:8080

# Use envsubst to replace the placeholder in the template and start nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /usr/share/nginx/html/index.template.html > /usr/share/nginx/html/index.html && exec nginx -g 'daemon off;'"]

EXPOSE 80
