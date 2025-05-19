# Simple Revit MCP Implementation

## A minimal and beginner-friendly implementation of the Model Context Protocol (MCP) for Autodesk Revit

---

**Why?**

After being frustrated with the multiple MCP for Revit implementations floating around the internet, I decided to try my hand at providing a simple, pyRevit-oriented MCP implementation. The goal is to make it as approachable as possible, even for those new to the Revit API.

**How?**

- This minimal implementation leverages the Routes module inside pyRevit to create a bridge between Revit and Large Language Models (LLMs).
- It provides a straightforward template to get started quickly, letting you prototype and iterate tools to give LLMs access to your Revit models.
- These tools are designed to be expanded for your specific use cases. You're very welcome to fork the repo and make your own contributions.
- **Note:** The pyRevit Routes API is currently in draft form and subject to change. It lacks built-in authentication mechanisms, so you'll need to implement your own security measures for production use.

**Batteries Included**

This repo is aimed at:
- Beginners to the Revit API
- Python specialists who aren't versed in C#
- Anyone wanting to prototype and iterate quickly with LLMs and Revit

It includes:
- A complete Routes implementation for pyRevit
- A minimal MCP server script to connect to any MCP-compatible client
- Several test commands to get you started right away

## Available Tools

The current implementation provides these key capabilities:

1. **Model Information** - Get comprehensive information about the Revit model:
   - Element counts by category (walls, doors, windows, etc.)
   - Room names and locations
   - Level information

2. **Get View** - Capture any Revit view for the LLM:
   - Export views as PNG images
   - Allow the model to view the image directly

3. **Family Placement** - Add elements to the Revit model:
   - Place family instances at specific coordinates
   - Set rotation and orientation
   - Apply custom properties to the placed elements

---

## Getting Started

### Installing uv:

**Mac:**
```bash
brew install uv
```

**Windows:**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
set Path=C:\Users\[username]\.local\bin;%Path%
```

For other platforms, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

### Setting Up the Project:

1. Fork or clone the repo: 
   ```
   https://github.com/JotaDeRodriguez/simple_revit_mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   uv venv
   
   # Activate it (Linux/Mac)
   source .venv/bin/activate
   
   # Activate it (Windows)
   .venv\Scripts\activate
   
   # Install requirements
   uv pip install -r requirements.txt
   ```

## Installing the Extension on Revit

1. In Revit, navigate to the pyRevit tab
2. Open Settings
3. Under "Custom Extensions", add the path to the `.extension` folder from this repo
4. Save settings and reload pyRevit (you might need to restart Revit entirely)

## Testing Your Connection

Once installed, test that the Routes API is working:

1. Open your web browser and go to:
   ```
   http://localhost:48884/revit_connector/status/
   ```

2. If successful, you should see a response like:
   ```json
   {"api_name": "revit_connector", "status": "active"}
   ```

The Routes Service will now load automatically whenever you start Revit. To disable it, simply remove the extension path from the pyRevit settings.

## Using the MCP Client

### Testing with the MCP Inspector

The MCP SDK includes a handy inspector tool for debugging:

```bash
mcp dev main.py
```

Then access `http://127.0.0.1:6274` in your browser to test your MCP server interactively.

### Connecting to Claude Desktop

The simplest way to install your MCP server in Claude Desktop:

```bash
mcp install main.py
```

Or for manual installation:

1. Open Claude Desktop → Settings → Developer → Edit Config
2. Add this to the `mcpServers` section:

```json
{
  "mcpServers": {
    "Revit Connector": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/absolute/path/to/main.py"
      ]
    }
  }
}
```

## Writing Your Own Functions

What makes this implementation special is how easy it is to create new endpoints:

1. **Define a Routes API endpoint in `startup.py`:**

```python
@api.route('/function/', methods=["GET"])
def some_function():
    # Access the current Revit document
    doc = revit.doc
    
    # Your Revit API logic here
    value = some_action(doc)
    
    return routes.make_response(data=value)
```

2. **Create a corresponding MCP tool in `main.py`:**

```python
@mcp.tool()
async def execute_function() -> str:
    """
    Description of what this tool does
    """
    try:
        url = f"{BASE_URL}/function/"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Creating Actions in the Model

For operations that modify the model, use POST requests with JSON payloads:

```python
# In startup.py
@api.route('/place_object/', methods=["POST"])
def place_object(request):
    # Get current document
    doc = revit.doc
    
    # Parse request data
    data = json.loads(request.data)
    
    # Start a transaction
    t = DB.Transaction(doc, "Place Object")
    t.Start()
    
    try:
        # Revit API logic to place an object
        # ...
        
        t.Commit()
        return routes.make_response(data={"status": "success"})
    except Exception as e:
        t.RollBack()
        return routes.make_response(
            data={"error": str(e)},
            status=500
        )
```

## Roadmap

This is a work in progress and more of a demonstration than a fully-featured product. Future improvements could include:

- **Testing with other MCP clients and more LLMs**
- **Creating a Dockerfile for seamless installation**
- **Authentication and security enhancements**
- **More advanced Revit tools and capabilities**
- **Better error handling and debugging features**
- **Documentation and examples for common use cases**
- **...**

## Contributing

Contributions are welcome! Feel free to submit pull requests or open issues for any bugs or feature requests.
Feel free to reach out to me if you have any questions, ideas