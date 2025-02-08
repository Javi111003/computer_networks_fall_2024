docker run --rm -d --name ftpd_server -p 21:21 -p 30000-30009:30000-30009 stilliard/pure-ftpd bash /run.sh -c 30 -C 10 -l puredb:/etc/pure-ftpd/pureftpd.pdb -E -j -R -P localhost -p 30000:30059
