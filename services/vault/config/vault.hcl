ui = true
listener "tcp" {
    address = "0.0.0.0:8200"
    tls_disable = 1
}

storage "file" {
    path = "/vault/data"
}

api_addr = "http://vault:8200"
cluster_addr = "http://vault:8201"

disable_mock = true
disable_cache = false