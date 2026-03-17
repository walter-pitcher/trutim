"""
AI Chat API - Streaming endpoint for Vercel AI SDK useChat
"""
import json
import os
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response


def extract_text_from_parts(parts):
    """Extract text content from message parts."""
    if not parts:
        return ""
    texts = []
    for p in parts:
        if isinstance(p, dict) and p.get("type") == "text":
            texts.append(p.get("text", ""))
    return "".join(texts)


def messages_to_openai(messages):
    """Convert UI messages to OpenAI API format."""
    result = []
    for msg in messages:
        role = msg.get("role", "user")
        parts = msg.get("parts", [])
        content = extract_text_from_parts(parts)
        if not content and role == "assistant":
            continue
        result.append({"role": role, "content": content or "(empty)"})
    return result


class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return StreamingHttpResponse(
                self._stream_error("OPENAI_API_KEY is not configured"),
                content_type="text/plain; charset=utf-8",
                status=500,
            )

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return StreamingHttpResponse(
                self._stream_error("Invalid JSON body"),
                content_type="text/plain; charset=utf-8",
                status=400,
            )

        messages = body.get("messages", [])
        if not messages:
            return StreamingHttpResponse(
                self._stream_error("No messages provided"),
                content_type="text/plain; charset=utf-8",
                status=400,
            )

        openai_messages = messages_to_openai(messages)
        if not openai_messages:
            return StreamingHttpResponse(
                self._stream_error("No valid messages"),
                content_type="text/plain; charset=utf-8",
                status=400,
            )

        system_prompt = (
            "You are a helpful AI assistant integrated into Trutim, a team collaboration app. "
            "Be concise, friendly, and helpful. Format responses clearly when appropriate."
        )
        # Prepend system message
        full_messages = [{"role": "system", "content": system_prompt}] + openai_messages

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            def generate():
                stream = client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=full_messages,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and getattr(delta, "content", None):
                        yield delta.content

            response = StreamingHttpResponse(
                generate(),
                content_type="text/plain; charset=utf-8",
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response

        except ImportError:
            return StreamingHttpResponse(
                self._stream_error("OpenAI package not installed. Run: pip install openai"),
                content_type="text/plain; charset=utf-8",
                status=500,
            )
        except Exception as e:
            return StreamingHttpResponse(
                self._stream_error(str(e)),
                content_type="text/plain; charset=utf-8",
                status=500,
            )

    def _stream_error(self, msg):
        def gen():
            yield msg

        return gen()


class AIImageView(APIView):
    """Generate an image using OpenAI DALL-E and return a permanent URL."""
    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return Response({"error": "OPENAI_API_KEY is not configured"}, status=500)

        prompt = request.data.get("prompt") or (request.data.get("text") if isinstance(request.data.get("text"), str) else None)
        if not prompt or not str(prompt).strip():
            return Response({"error": "Prompt is required"}, status=400)

        try:
            from openai import OpenAI
            from django.core.files.base import ContentFile
            from django.core.files.storage import default_storage
            import requests
            import uuid

            client = OpenAI(api_key=api_key)
            response = client.images.generate(
                model=os.environ.get("OPENAI_IMAGE_MODEL", "dall-e-3"),
                prompt=str(prompt).strip()[:4000],
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            if not image_url:
                return Response({"error": "No image URL returned"}, status=500)

            # Download and save to our storage for permanence
            r = requests.get(image_url, timeout=30)
            r.raise_for_status()
            ext = ".png"
            path = default_storage.save(f"ai_images/{uuid.uuid4().hex}{ext}", ContentFile(r.content))
            url = default_storage.url(path)
            if url.startswith("/"):
                url = request.build_absolute_uri(url)

            return Response({"url": url, "prompt": str(prompt).strip()})
        except ImportError:
            return Response({"error": "OpenAI package not installed"}, status=500)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
