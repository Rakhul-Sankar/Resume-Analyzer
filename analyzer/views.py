# views.py
from django.http import HttpResponse
from pdf2image import convert_from_bytes
import pytesseract

def analyze_pdf(request):
    file = request.FILES.get('resume')
    if not file:
        return HttpResponse("No file uploaded", status=400)

    # Convert PDF pages to images
    images = convert_from_bytes(file.read())
    text = ""

    for img in images:
        text += pytesseract.image_to_string(img) + "\n"

    return HttpResponse(text)
