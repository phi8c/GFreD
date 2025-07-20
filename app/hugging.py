from transformers import pipeline
from extract_text import extract_chapters_from_pdf, extract_chapters_from_pdffs
from pprint import pprint
#import fitz  # <-- đúng, đây là alias chính thức của PyMuPDF




# Tải pipeline sinh văn bản từ BLOOM
#generator = pipeline("text-generation", model="tiiuae/falcon-rw-1b")

# Prompt tạo câu hỏi trắc nghiệm
#prompt = "Hãy tạo 5 câu hỏi trắc nghiệm về trí tuệ nhân tạo."

# Gọi API sinh câu hỏi
#result = generator(prompt, max_length=200, num_return_sequences=1)

#print(result[0]['generated_text'])
chapters = extract_chapters_from_pdffs("D:\\ADAV\\KTVM.pdf", "output/images")




pprint(chapters)
sochuong = len(chapters)

print("in ra so chuong", sochuong)
for i, ch in enumerate(chapters):
    print(f"\n🔹 Chương {i+1}: {ch['title']}")
    print(f"📄 Độ dài văn bản: {len(ch['text'])} ký tự")
    print(f"🖼️ Số ảnh: {len(ch['images'])}")

