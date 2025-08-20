import asyncio
from wove import weave, merge

# Current methodology
async def main():
    async with weave() as w:
        @w.do
        async def f1():
            return range(100)

        @w.do
        async def f2(f1):
            return await merge(lambda x: x**2, f1)

        @w.do
        async def f3(f2):
            return sum(f2)
    print(w.result.final)
asyncio.run(main())

# New methodology
async def main():
    async with weave() as w:
        @w.do
        async def f1():
            return range(100)

        @w.do(f1)
        async def f2(f1):
            return f1**2

        @w.do
        async def f3(f2):
            return sum(f2)
    print(w.result.final)
asyncio.run(main())