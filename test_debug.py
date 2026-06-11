from backend.security.proxy import AlluciSecureProxy
proxy = AlluciSecureProxy()
packet = proxy.process_outbound_prompt("Hello John Doe and my email is test@example.com.")
print(packet.secure_ephemeral_vault)
