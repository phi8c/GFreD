from openai import OpenAI
import json
import re
import base64
import random
from dotenv import load_dotenv
import os

load_dotenv()










# client = OpenAI(
#     api_key="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"
# )

# Lấy API key từ môi trường
api_key = os.getenv("OPENAI_API_KEY")

# Tạo client OpenAI với API key
client = OpenAI(api_key=api_key)









def generate_questions(text, num_questions):
    if not text or num_questions <= 0:
        return []

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý sinh câu hỏi trắc nghiệm. Hãy trả về dữ liệu dưới dạng JSON."},
                {"role": "user", "content": f"Hãy tạo {num_questions} câu hỏi trắc nghiệm từ đoạn văn sau. Mỗi câu hỏi có 4 đáp án và 1 đáp án đúng:\n{text}"}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        response_content = response.choices[0].message.content.strip()
        cleaned_json_str = re.sub(r"```json\s*|\s*```", "", response_content).strip()
        questions_data = json.loads(cleaned_json_str)

        if isinstance(questions_data, list):
            return questions_data
        elif isinstance(questions_data, dict):
            return questions_data.get("questions", [])
        else:
            print("🚨 Dữ liệu không hợp lệ:", questions_data)
            return []

    except Exception as e:
        print(f"❌ Lỗi khi gọi API hoặc xử lý JSON: {e}")
        return []
#### MỚI THÊM VÀO

def generate_questions_advance(text, num_questions):
    if not text or num_questions <= 0:
        return []

    try:
        prompt = f"""
Tạo {num_questions} câu hỏi trắc nghiệm từ đoạn văn sau.

Yêu cầu mỗi câu hỏi có cấu trúc JSON như sau:
{{
  "question": "Nội dung câu hỏi?",
  "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
  "correct_answer": "A"
}}

❗ Lưu ý:
- Trường `correct_answer` phải là 1 trong các ký tự: "A", "B", "C", hoặc "D" — **không được là đoạn văn hoặc giải thích**.
- Trả về danh sách JSON gồm các câu hỏi, không có văn bản thừa, không có markdown, không có giải thích.
- Dữ liệu trả về phải đúng định dạng JSON.

Đoạn văn:
{text}
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý sinh câu hỏi trắc nghiệm. Hãy trả về dữ liệu dưới dạng JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )

        response_content = response.choices[0].message.content.strip()
        cleaned_json_str = re.sub(r"```json\s*|\s*```", "", response_content).strip()
        questions_data = json.loads(cleaned_json_str)

        if isinstance(questions_data, list):
            return questions_data
        elif isinstance(questions_data, dict):
            return questions_data.get("questions", [])
        else:
            print("🚨 Dữ liệu không hợp lệ:", questions_data)
            return []

    except Exception as e:
        print(f"❌ Lỗi khi gọi API hoặc xử lý JSON: {e}")
        return []




##### KÊT THÚC

def generate_questions_from_jobs(text, jobs):
    
    #prompt_jobs = "Từ nội dung trên, tạo câu hỏi trắc nghiệm như sau:\n"
    all_questions = []

    for job in jobs:
        chapter = job["chuong"]
        level = job["do_kho"]
        count = job["so_luong"]
        if level == "de":
            prompt = f"""
Từ nội dung sau, hãy tạo {count} câu hỏi trắc nghiệm chương {chapter} với độ khó: dễ.
Mỗi câu hỏi gồm:
- 1 câu hỏi
- 4 đáp án A–D
- 1 đáp án đúng
Trả về danh sách JSON theo mẫu sau:
[
  {{
    "chuong": {chapter},
    "do_kho": "de",
    "cau_hoi": "...",
    "dap_an": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "dap_an_dung": "A"
  }},
  ...
]
"""

        elif level == "trung_binh":
            prompt = f"""
Từ nội dung sau, hãy tạo {count} câu hỏi trắc nghiệm chương {chapter} với độ khó: trung bình.

Yêu cầu:
- Câu hỏi nên không chỉ hỏi về khái niệm, mà khai thác các đặc điểm, phân loại, chức năng, hoặc mối quan hệ giữa các đối tượng liên quan.
- Nên có yếu tố phân tích hoặc so sánh (ví dụ: điểm giống và khác giữa hai kỹ thuật, hai phương pháp, hai đối tượng...).
- Tránh hỏi lại nguyên văn nội dung bài giảng.

Trả về danh sách JSON theo mẫu sau:
[
  {{
    "chuong": {chapter},
    "do_kho": "trung_binh",
    "cau_hoi": "...",
    "dap_an": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "dap_an_dung": "A"
  }},
  ...
]
"""

        elif level == "kho":
            prompt = f"""
Từ nội dung sau, hãy tạo {count} câu hỏi trắc nghiệm chương {chapter} với độ khó: khó.

Yêu cầu:
- Câu hỏi mang tính vận dụng cao, có thể lồng ghép tình huống thực tế.
- Nên yêu cầu người học suy luận, đánh giá hoặc ứng dụng kiến thức vào các tình huống cụ thể trong thực tế hoặc chuyên ngành.
- Câu hỏi không được đơn thuần lặp lại thông tin trong bài giảng mà phải đòi hỏi hiểu sâu hoặc vận dụng sáng tạo.
- Có thể dùng ví dụ, dữ liệu giả định, hoặc tình huống phù hợp với lĩnh vực (nhưng không bắt buộc viết mã nếu không phù hợp ngành).

Trả về danh sách JSON theo mẫu sau:
[
  {{
    "chuong": {chapter},
    "do_kho": "kho",
    "cau_hoi": "...",
    "dap_an": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "dap_an_dung": "A"
  }},
  ...
]
"""
#         prompt = f"""
# Từ nội dung sau, hãy tạo {count} câu hỏi trắc nghiệm chương {chapter} với độ khó: {level}.
# Mỗi câu hỏi gồm:
# - 1 câu hỏi
# - 4 đáp án A–D
# - 1 đáp án đúng
# Trả về danh sách JSON theo mẫu sau:
# [
#   {{
#     "chuong": {chapter},
#     "do_kho": "{level}",
#     "cau_hoi": "...",
#     "dap_an": {{
#       "A": "...",
#       "B": "...",
#       "C": "...",
#       "D": "..."
#     }},
#     "dap_an_dung": "A"
#   }},
#   ...
# ]
# """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý sinh câu hỏi trắc nghiệm."},
                {"role": "user", "content": text},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )

        response_content = response.choices[0].message.content.strip()
        print("✅ Chuỗi phản hồi:", response_content)
        # cleaned_json_str = re.sub(r"```json\s*|\s*```", "", response_content).strip()
        cleaned_json_str = extract_clean_json(response_content)
        if not cleaned_json_str:
         #data = json.loads(cleaned_json_str)
         print("🚨 Không lấy được JSON hợp lệ từ response!")
         return []
    # xử lý tiếp...
        # else:
        #  print("🚨 Không lấy được JSON hợp lệ từ response!")
        try:
            data = json.loads(cleaned_json_str)
            print("✅ In ra data sau khi parse:", data)
            if isinstance(data, list):
                all_questions.extend(data)
            elif isinstance(data, dict) and "questions" in data:
                all_questions.extend(data["questions"])
                print("✅ Danh sách câu hỏi đã xử lý ở dạng nâng cao!!:", all_questions)
        except json.JSONDecodeError:
            print(f"🚨 Lỗi JSON ở chương {chapter}, độ khó {level}:", response_content)

    return all_questions
def extract_clean_json(text):
    """
    Hàm làm sạch phản hồi từ GPT: loại bỏ phần mô tả, ```json code block, chỉ lấy JSON thuần.
    """

    if not text:
        return None

    
    cleaned_text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip("`\n ")

    # Tìm đoạn bắt đầu bằng [ hoặc { và kết thúc bằng ] hoặc }
    matches = re.findall(r'(\[\s*{.*?}\s*\])', cleaned_text, re.DOTALL)
    if not matches:
        matches = re.findall(r'(\{.*?\})', cleaned_text, re.DOTALL)

    for match in matches:
        try:
            # Kiểm tra xem đoạn có parse được không
            json.loads(match)
            return match.strip()
        except json.JSONDecodeError:
            continue

    print("🚨 Không tìm thấy JSON hợp lệ trong phản hồi!")
    return None


#
#

# TỪ ĐÂY LÀ HÀM SINH CÂU HỎI CÓ HÌNH ẢNH

def encode_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def build_image_prompt(caption, context):
    return f"""
Bạn là trợ lý giáo dục. Dưới đây là một hình ảnh từ bài giảng cùng mô tả và đoạn nội dung ngữ cảnh. 
Hãy sinh 1 câu hỏi trắc nghiệm gồm 4 đáp án A, B, C, D liên quan đến hình ảnh và mô tả. 
Hãy trả về kết quả ở định dạng JSON sau:

{{
  "question_text": "...",
  "option_a": "...",
  "option_b": "...",
  "option_c": "...",
  "option_d": "...",
  "correct_answer": "..."
}}

Mô tả ảnh: {caption}

Ngữ cảnh chương: {context}
"""

def call_gpt_with_image(prompt, image_path):
    base64_img = encode_image_base64(image_path)

    messages = [
        {"role": "system", "content": "Bạn là trợ lý giáo dục."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{base64_img}"
                }}
            ]
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )

    return response["choices"][0]["message"]["content"]

def generate_questions_from_images(chapters, max_img_per_chapter=2):
    all_questions = []

    for chapter in chapters:
        context = chapter['text'][:1000]
        images = chapter.get("images", [])
        #selected_images = random.sample(images, min(len(images), max_img_per_chapter))
        selected_images = random.sample(images, 1) if images else []

        for img in selected_images:
            prompt = build_image_prompt(img.get("caption", ""), context)

            try:
                response = call_gpt_with_image(prompt, img["path"])
                question_json = json.loads(response)

                question = {
                    **question_json,
                    "type": "image",
                    "chapter_title": chapter["title"],
                    "image_path": img["path"],
                    "source_text": img.get("caption", "")
                }

                all_questions.append(question)

            except Exception as e:
                print(f"[LỖI]: Không thể sinh câu hỏi cho ảnh {img['path']}: {e}")

    return all_questions
def extract_json_block(text):
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text  # fallback nếu không có markdown




# KẾT THÚC CÂU HỎI CÓ HÌNH ẢNH
#
#
# SINH CÂU HỎI DẠNG TN THPT 2025 CÓ HÌNH ẢNH



def build_image_prompt_tf(caption, context):
    return f"""
Bạn là trợ lý giáo dục. 
 Nhiệm vụ:
- Hãy tạo **một câu hỏi đúng/sai** gồm:
  • Một **nội dung chính** đặt dưới hình ảnh (ví dụ: "Hình ảnh trên mô tả...").
  • Bốn **mệnh đề phụ** liên quan đến nội dung chính và hình ảnh.
- Mỗi mệnh đề phải thể hiện rõ ràng đó là **Đúng** hay **Sai**.
Trả kết quả theo định dạng JSON như sau:

{{
  "main_statement": "...",
  "sub_statements": [
    {{
      "statement": "...",
      "is_true": true
    }},
    ...
  ]
}}

Mô tả ảnh: {caption}

Ngữ cảnh chương: {context[:800]}
"""

def build_image_prompt_short(caption, context):
    return f"""
Bạn là trợ lý giáo dục. Dưới đây là một hình ảnh từ bài giảng cùng mô tả và đoạn nội dung ngữ cảnh. 
Tạo 1 câu hỏi trả lời ngắn (1-3 câu) liên quan tới ảnh sau. Câu hỏi phải yêu cầu suy luận hoặc vận dụng.

Trả kết quả JSON như sau:

{{
  "question_text": "...",
  "answer": "..."
}}

Mô tả ảnh: {caption}

Ngữ cảnh chương: {context[:800]}
"""

def call_gpt_with_images(prompt, image_path):
    base64_img = encode_image_base64(image_path)
    print(f"🧪 Base64 ảnh có độ dài: {len(base64_img)}")


    messages = [
        {"role": "system", "content": "Bạn là trợ lý giáo dục."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{base64_img}"
                }}
            ]
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )
    
    content = response.choices[0].message.content.strip()
    print(f"✅ Nội dung trả về:", content)

    return response.choices[0].message.content.strip()


def generate_mcq_questions(text, num_questions):
    prompt = f"""
Từ nội dung sau, hãy sinh {num_questions} câu hỏi trắc nghiệm 4 lựa chọn A, B, C, D. 
Yêu cầu:
- Không được hỏi về chương hoặc tiêu đề chương.
- Câu hỏi phải tập trung vào các **khái niệm**, **nội dung chính**, **đặc điểm**, hoặc **ứng dụng thực tế** được trình bày trong văn bản.
Mỗi câu có đúng 1 đáp án. Trả về dưới dạng JSON như ví dụ:

[
  {{
    "question_text": "...",
    "option_a": "...",
    "option_b": "...",
    "option_c": "...",
    "option_d": "...",
    "correct_answer": "A"
  }},
  ...
]

Nội dung:
{text[:1500]}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Bạn là trợ lý sinh câu hỏi trắc nghiệm. Hãy trả về dữ liệu dưới dạng JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.7
    )

    content = response.choices[0].message.content
    cleaned = re.sub(r"```json|```", "", content).strip()
    return json.loads(cleaned)

def generate_true_false_questions(text, num_questions):
    prompt = f"""
Hãy tạo {num_questions} câu hỏi đúng/sai dạng nâng cao theo cấu trúc sau:
- Mỗi câu gồm 1 câu hỏi chính (main_statement) và 4 mệnh đề phụ (sub_statements).
- Các câu hỏi cần mang tính ứng dụng, so sánh, hoặc đánh đố. Không đơn thuần trích lại nội dung từ tài liệu.
- Câu hỏi có thể yêu cầu người học suy luận, phân tích hoặc liên hệ thực tế.
- Chỉ sử dụng nội dung sau để xác định chủ đề, KHÔNG lấy trực tiếp thông tin từ đó để làm câu hỏi.
- Trả kết quả phải theo định dạng JSON như sau:

[
  {{
    "main_statement": "...",
    "sub_statements": [
      {{
        "statement": "...",
        "is_true": true
      }},
      ...
    ]
  }},
  ...
]

Nội dung:
{text[:1500]}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Bạn là trợ lý giáo dục."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.7
    )

    content = response.choices[0].message.content
    print("🧪 Nội dung raw trả về từ GPT:")
    print(content)
    json_string = extract_json_block(content)
    print("in ra phản hồi sau khi ép kiểu: ", json_string)
    cleaned = re.sub(r"```json|```", "", content).strip()
    print(" in ra cleaned của hàm sinh câu hỏi tf text", cleaned)
    return json.loads(cleaned)

def generate_short_answer_questions(text, num_questions):
    prompt = f"""
Tạo {num_questions} câu hỏi trả lời ngắn (1-3 câu) từ nội dung sau. Câu hỏi nên yêu cầu suy luận, vận dụng hoặc phân tích, một tình huống thực tế. Đáp án là một con số, một cái tên, một sự vật hiện tượng cụ thể

Trả về dưới dạng JSON:

[
  {{
    "question_text": "...",
    "answer": "..."
  }},
  ...
]

Nội dung:
{text[:1500]}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Bạn là trợ lý giáo dục."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.7
    )

    content = response.choices[0].message.content
    cleaned = re.sub(r"```json|```", "", content).strip()
    return json.loads(cleaned)

def generate_tf_with_images(chapters, max_img=4):
    results = []
    for chapter in chapters:
        context = chapter['text']
        images = chapter.get("images", [])
        selected = random.sample(images, min(len(images), max_img))

        for img in selected:
            try:
                print(f"\n Đang xử lý ảnh: {img['path']}")
                prompt = build_image_prompt_tf(img.get("caption", ""), context)
                
                raw = call_gpt_with_images(prompt, img["path"])
                print(f" Prompt:\n{prompt[:500]}")
                json_string = extract_json_block(raw)
                print("in ra json string sau khi đc ép từ hàm", json_string)
                parsed = json.loads(json_string)
                parsed["chapter_title"] = chapter["title"]
                parsed["image_path"] = img["path"]
                results.append(parsed)
                
            except Exception as e:
                print(f"❌ Lỗi sinh câu hỏi đúng/sai từ ảnh: {e}")
    print("in ra result trong hàm sinh câu hỏi có ảnh", results)

    return results

def generate_short_with_images(chapters):
    results = []
    for chapter in chapters:
        context = chapter['text']
        images = chapter.get("images", [])
        for img in images:
            try:
                prompt = build_image_prompt_short(img.get("caption", ""), context)
                raw = call_gpt_with_image(prompt, img["path"])
                parsed = json.loads(raw)
                parsed["chapter_title"] = chapter["title"]
                parsed["image_path"] = img["path"]
                results.append(parsed)
            except Exception as e:
                print(f"❌ Lỗi sinh câu hỏi trả lời ngắn từ ảnh: {e}")
    return results






# KẾT THÚC SINH CÂU HỎI DẠNG TN THPT 2025 CÓ HÌNH ẢNH
    
    

    
    




