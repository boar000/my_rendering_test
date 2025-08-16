from fastapi import FastAPI
import RenderingTestLib as rt
import importlib
app = FastAPI()

@app.get("/test-ci/{test_name}")
async def read_item(test_name: str):
    testcases = rt.gather_test_cases()
    found = next((x for x in testcases if x.name == test_name), None)
    
    if found is not None:
        references = rt.load_reference_images()
        result = rt.run_test(found, references)

        return {"result": "True" if len(result.failed) == 0 else "False" }
    
    return {"result": "Data not found" }