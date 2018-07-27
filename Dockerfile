FROM lowerquality/gentle:latest as gentle

WORKDIR /gentle

ENV PORT=8765
EXPOSE 8765

CMD /usr/bin/python serve.py --port $PORT
