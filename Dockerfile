FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY testBlog/ /app
COPY ./requirements.txt /tmp/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Conditionally install django-q2
ARG USE_DJANGO_Q=False
RUN if [ "$USE_DJANGO_Q" = True ] ; then pip install django-q2 ; fi

EXPOSE 8000
RUN ["chmod", "+x", "/app/entrypoint.sh"]
CMD ["/app/entrypoint.sh"]
