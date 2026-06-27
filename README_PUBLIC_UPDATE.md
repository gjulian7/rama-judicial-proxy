# Rama Judicial Proxy, public endpoint update

Replace only this file in your GitHub repo:

```text
main.py
```

This update adds:

```text
/rama/public/seven-elephants
```

This endpoint does not require the X-API-Key header.

Your protected endpoints remain:

```text
/rama/seven-elephants
/rama/procesos
```

After Render redeploys, open this in a normal browser:

```text
https://rama-judicial-proxy.onrender.com/rama/public/seven-elephants
```
