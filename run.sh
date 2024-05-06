#!/bin/bash

sudo docker compose down -v --rmi all
sudo docker compose up --build