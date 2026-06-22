
with open('backend/tests/test_routers_channels.py', 'r') as f:
    content = f.read()

# I will find the last index of `async def test_oauth_callback(self, app_client, mock_adapters):` which is line 258
# and replace everything after that. Actually, I appended it, so I can just find `async def test_channels_error_paths`
idx = content.find('    @pytest.mark.asyncio\n    async def test_channels_error_paths(self, app_client, mock_adapters):')
if idx != -1:
    content = content[:idx]

with open('backend/tests/test_routers_channels.py', 'w') as f:
    f.write(content)

