import os
import json
import traceback
from openai import AsyncOpenAI
from typing import AsyncGenerator, List, Dict, Any, Optional
from .base import LLMProvider

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, system_prompt: str, model_name: str = None, tool_definitions: List[Dict] = None, tool_implementations: Dict[str, Any] = None):
        # Use custom OpenAI-compatible API
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.letsdisagree.com/v1")
        self.api_key = os.getenv("LLM_API_KEY", api_key)

        if model_name is None:
            model_name = os.getenv("LLM_MODEL", "ag/gemini-3-flash")

        print(f"Initializing LLM with model: {model_name} at {self.base_url}")

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.tool_definitions = tool_definitions
        self.tool_implementations = tool_implementations

    async def generate_response(self, text_input: str) -> AsyncGenerator[str, None]:
        print(f"[LLM] Sending request: '{text_input}'")

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": text_input})

        # Loop to handle potential multiple tool calls (chaining)
        # though usually it's just one round of tools then final answer
        while True:
            try:
                # Prepare args
                kwargs = {
                    "model": self.model_name,
                    "messages": self.conversation_history,
                    "stream": True
                }
                if self.tool_definitions:
                    kwargs["tools"] = self.tool_definitions

                stream = await self.client.chat.completions.create(**kwargs)

                print("[LLM] Stream started")
                full_content = ""
                tool_calls_buffer = {} # Index -> {id, name, args_parts}
                
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                        
                    delta = chunk.choices[0].delta
                    
                    # Handle Text Content
                    if delta.content:
                        full_content += delta.content
                        yield delta.content

                    # Handle Tool Calls (Accumulate)
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_buffer:
                                tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}
                            
                            if tc.id:
                                tool_calls_buffer[idx]["id"] += tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_buffer[idx]["name"] += tc.function.name
                                if tc.function.arguments:
                                    tool_calls_buffer[idx]["arguments"] += tc.function.arguments

                # End of stream for this turn
                
                # If we have content, append to history
                if full_content:
                    self.conversation_history.append({"role": "assistant", "content": full_content})

                # If no tool calls, we are done
                if not tool_calls_buffer:
                    print("[LLM] Stream finished (No tools)")
                    break
                
                # Process Tool Calls
                print(f"[LLM] Processing {len(tool_calls_buffer)} tool calls")
                
                # Construct the tool_calls list for the assistant message
                tool_calls_msg = []
                for idx in sorted(tool_calls_buffer.keys()):
                    tc_data = tool_calls_buffer[idx]
                    # Some proxies might not return an ID if it's implicit, but OpenAI standard requires it.
                    # We generate a fallback if missing, though it might fail if API is strict.
                    call_id = tc_data["id"] if tc_data["id"] else f"call_{idx}_{os.urandom(4).hex()}"
                    
                    tool_calls_msg.append({
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tc_data["name"],
                            "arguments": tc_data["arguments"]
                        }
                    })

                # Append the assistant's tool_call message to history
                if full_content:
                    # Update the last message to include tool_calls
                    self.conversation_history[-1]["tool_calls"] = tool_calls_msg
                else:
                    self.conversation_history.append({
                        "role": "assistant", 
                        "content": None,
                        "tool_calls": tool_calls_msg
                    })

                # Execute Tools and Generate Tool Outputs
                for tc in tool_calls_msg:
                    func_name = tc["function"]["name"]
                    func_args_str = tc["function"]["arguments"]
                    call_id = tc["id"]
                    
                    print(f"[LLM] Executing tool: {func_name}({func_args_str})")
                    
                    result_content = "Error: Tool not found"
                    if self.tool_implementations and func_name in self.tool_implementations:
                        try:
                            # Basic argument parsing (handles empty string case)
                            if not func_args_str:
                                args = {}
                            else:
                                args = json.loads(func_args_str)
                                
                            # Call the function
                            # Note: Assuming synchronous tools for now as per our 'basic.py'
                            result = self.tool_implementations[func_name](**args)
                            result_content = json.dumps(result)
                        except Exception as e:
                            result_content = f"Error executing tool: {str(e)}"
                            print(f"[LLM] Tool execution error: {e}")
                            traceback.print_exc()
                    else:
                        print(f"[LLM] Warning: Tool {func_name} not implemented")
                    
                    # Append Tool Message
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result_content
                    })
                    print(f"[LLM] Tool Output: {result_content}")

                # Loop continues to send the tool outputs back to LLM and get final response

            except Exception as e:
                print(f"[LLM] Error: {e}")
                traceback.print_exc()
                yield f" I'm sorry, I encountered an error: {str(e)}"
                break