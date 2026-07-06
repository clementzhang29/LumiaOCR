import asyncio, httpx

async def main():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8080', timeout=300.0) as c:
        r = await c.post('/api/providers', json={'name':'test','base_url':'https://api.openai.com/v1','api_key':'sk-test','model':'gpt-4o-mini'})
        print('Provider:', r.status_code)

        with open('tests/test_sample.pdf', 'rb') as f:
            r = await c.post('/api/convert', files={'file':('test_sample.pdf',f,'application/pdf')}, data={'strategy':'auto','preferred_engine':'docling'})
        print('Upload:', r.status_code, r.json())
        tid = r.json()['task_id']

        for i in range(180):
            try:
                r = await c.get('/api/status/'+tid)
            except Exception as e:
                print(f'poll #{i} connection error: {type(e).__name__}')
                await asyncio.sleep(3)
                continue
            info = r.json()
            s = info.get('status')
            if s == 'completed':
                res = await c.get('/api/result/'+tid)
                d = res.json()
                print()
                print('=== Result ===')
                print('Engine:', d.get('engine_used'))
                print('Quality:', d.get('quality_score'))
                md = d.get('markdown','')
                print('MD chars:', len(md))
                if md:
                    print('Preview:', md[:300])
                result = 'PASS' if len(md)>0 else 'FAIL - empty md'
                print(result)
                break
            elif s == 'failed':
                print('Failed:', info.get('error','?'))
                break
            else:
                if i % 10 == 0:
                    print(f'poll #{i}: {s}')
                await asyncio.sleep(2)

asyncio.run(main())
