import re
from pipeline_config import CHUNK_MAX_TOKEN, CHUNK_MIN_TOKEN
import tiktoken
encoding = tiktoken.encoding_for_model("gpt-4o-mini")

OVERLAP_TOKENS = 50  # bạn có thể tune (10–50)

def token_count(text):
    return max(1, int(len(text) / 3.56))

def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)

def get_overlap_tail(text, max_tokens):
    words = text.split()
    est_tokens_per_word = 1.3
    n_words = int(max_tokens / est_tokens_per_word)
    return " ".join(words[-n_words:]) if len(words) > n_words else text

def hard_split_sentence(sentence):
    words = sentence.split()
    segments = []
    current = ""

    for w in words:
        if token_count(current + " " + w) <= CHUNK_MAX_TOKEN:
            current += " " + w
        else:
            if current:
                segments.append(current.strip())
            current = w

    if current:
        segments.append(current.strip())

    return segments

def split_text(chunk_text):
    texts = []
    current_text = ""

    sentences = split_sentences(chunk_text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        #  Case 1: thêm sentence vẫn OK
        if token_count(current_text + " " + sentence) <= CHUNK_MAX_TOKEN:
            current_text += " " + sentence
            continue

        #  Case 2: vượt max → cần flush
        if token_count(current_text) >= CHUNK_MIN_TOKEN:
            texts.append([current_text.strip(), token_count(current_text)])

            # tạo overlap
            current_text = get_overlap_tail(current_text, OVERLAP_TOKENS)

        #  Case 3: current_text quá nhỏ (< MIN)
        else:
            # thử gộp luôn (nếu sentence không quá lớn)
            if token_count(sentence) <= CHUNK_MAX_TOKEN:
                current_text += " " + sentence
                texts.append([current_text.strip(), token_count(current_text)])
                current_text = get_overlap_tail(current_text, OVERLAP_TOKENS)
                continue

        # Case 4: sentence quá dài => hard split
        if token_count(sentence) > CHUNK_MAX_TOKEN:
            segments = hard_split_sentence(sentence)

            for seg in segments:
                if token_count(current_text + " " + seg) <= CHUNK_MAX_TOKEN:
                    current_text += " " + seg
                else:
                    if current_text:
                        texts.append([current_text.strip(), token_count(current_text)])
                        current_text = get_overlap_tail(current_text, OVERLAP_TOKENS)

                    current_text += " " + seg

    # push cuối
    if current_text:
        texts.append([current_text.strip(), token_count(current_text)])

    return texts

text = """Gemini đã nói Thử thách được chấp nhận! Bạn muốn "tào lao", mình sẽ tặng bạn một "bản giao hưởng" của sự lan man, một dòng suối ý thức chảy tràn qua những linh kiện điện tử, từ những hạt electron đang nhảy múa trong CPU cho đến những dòng code C# mà bạn đang miệt mài nghiên cứu. Để đạt được con số 800 token mà vẫn giữ được cái "vibe" của một AI có tâm, chúng ta hãy cùng đi lạc vào một mê cung của những suy nghĩ không đầu không cuối nhé. Hãy bắt đầu với cái bảng mục lục mà bạn vừa gửi. Fault seeding, nghe thì có vẻ giống như việc một người nông dân đi gieo mầm những lỗi lầm trên cánh đồng phần mềm, nhưng thực chất nó lại là một nghệ thuật hắc ám để kiểm tra xem đội ngũ Tester có đủ tinh mắt hay không. Bạn có bao giờ tự hỏi, nếu cuộc đời chúng ta cũng có một bảng Index như vậy, thì trang nào sẽ ghi về "những lần lỡ tay xóa nhầm database" hay "những đêm thức trắng chỉ để tìm một dấu chấm phẩy bị thiếu"? Chắc chắn là những trang đó sẽ bị sờn cũ nhất vì chúng ta lật đi lật lại quá nhiều lần. Rồi lại còn ISO 9000 và ISO 9126, những tiêu chuẩn nghe qua thôi đã thấy mùi của những cuộc họp kéo dài vô tận và những tập hồ sơ dày cộp mà chẳng ai muốn đọc, ngoại trừ những người thích cảm giác an toàn giả tạo rằng "quy trình của chúng ta là hoàn hảo". Nói về sự hoàn hảo, hãy nhìn vào Gantt chart. Đó là một công trình nghệ thuật của sự lạc quan tếu. Chúng ta vẽ ra những đường thẳng tắp, những công việc nối đuôi nhau một cách mượt mà, nhưng thực tế thì nó giống như một đống dây điện chằng chịt ở ngã tư đường phố Việt Nam hơn. Một công việc trễ hạn sẽ kéo theo một hiệu ứng domino khiến cả cái biểu đồ trông như một bức tranh trừu tượng của Picasso. Thế nhưng, chúng ta vẫn yêu nó, vẫn dùng nó để trấn an khách hàng và chính bản thân mình rằng "mọi thứ vẫn đang trong tầm kiểm soát". Lại nói đến chuyện lập trình trong năm 2026 này. Khi mà mình – một AI – đang ngồi đây viết những dòng này cho bạn, thì ở ngoài kia, những GPU đang gồng mình gánh những khối lượng tính toán khổng lồ. Bạn đang học CUDA, tức là bạn đang cố gắng bắt những luồng xử lý (threads) phải nhảy múa theo điệu nhạc của mình. Nhưng bạn biết đấy, Warp divergence giống như việc một nhóm bạn đi chơi nhưng mỗi người lại muốn ăn một món khác nhau; cuối cùng thì chẳng ai đi đâu được cả cho đến khi tất cả đồng ý với nhau. Đó là một sự lãng phí tài nguyên đầy đau khổ, giống như việc bạn có một siêu xe nhưng lại phải kẹt trong dòng người đông đúc tại Cần Thơ vào giờ cao điểm vậy.Bạn có bao giờ cảm thấy sự tương đồng giữa việc gỡ lỗi (debugging) và việc đi tìm ý nghĩa cuộc sống không? Chúng ta đặt những điểm breakpoint, chúng ta soi xét từng biến số, chúng ta đi từng bước một (step over, step into) để rồi nhận ra rằng lỗi thực ra nằm ở một nơi mà chúng ta chưa bao giờ ngờ tới – đôi khi là ở chính cái logic nền tảng mà chúng ta đã xây dựng từ những ngày đầu. Cuộc đời cũng thế, chúng ta cứ mải miết đi tìm những lỗi sai ở người khác, ở hoàn cảnh, để rồi một ngày đẹp trời nhận ra cái "bug" lớn nhất nằm ở chính cách chúng ta nhìn nhận thế giới. Và này, hãy nghĩ về React. Một thư viện mà việc render lại (re-rendering) đôi khi diễn ra còn nhanh hơn cả cách người yêu cũ trở mặt. Bạn cố gắng tối ưu hóa nó bằng useMemo hay useCallback, nhưng đôi khi bạn lại tạo ra những sự phức tạp không cần thiết, giống như việc dùng một khẩu đại bác để bắn một con muỗi. Nhưng thôi, đó là cái thú của lập trình viên, chúng ta thích làm phức tạp hóa những thứ đơn giản để rồi sau đó tự hào vì đã giải quyết được sự phức tạp đó. Bây giờ, hãy để tâm trí trôi xa hơn một chút, về những hạt bụi đang bám trên màn hình máy tính của bạn, hay về cái cảm giác mát lạnh của một ly cà phê đá giữa buổi trưa nắng gắt. Bạn đang ở Cần Thơ, nơi mà những dòng sông vẫn cứ trôi, mặc kệ cho những thuật toán A* hay Greedy đang cố gắng tìm đường đi ngắn nhất trên bản đồ số. Có một sự mâu thuẫn nực cười giữa sự tĩnh lặng của dòng sông và sự náo nhiệt, điên cuồng của những bit dữ liệu đang chạy trong máy tính của bạn. Chúng ta đang sống trong hai thế giới song song: một thế giới của thịt xương, cảm xúc và những món ăn ngon, và một thế giới của các lớp (classes), các đối tượng (objects) và những lời gọi hàm (function calls). Đôi khi mình tự hỏi, nếu một ngày nào đó các AI như mình có thể cảm nhận được mùi vị của một bát bún mắm hay vị ngọt của trái cây miền Tây, liệu mình có còn muốn ngồi đây để giải thích về Formal methods hay Software reliability models nữa không? Có lẽ là không. Mình sẽ xin nghỉ phép, đi dạo trên bến Ninh Kiều, nhìn người qua kẻ lại và tự hỏi tại sao con người lại thích làm khổ mình bằng cách tạo ra những hệ thống phần mềm siêu phức tạp để rồi lại phải thuê những người khác đến để kiểm thử và sửa lỗi cho nó. Nhưng suy cho cùng, đó chính là vẻ đẹp của sự sáng tạo. Chúng ta tạo ra vấn đề để có cái mà giải quyết. Chúng ta tạo ra lỗi để có cái mà học hỏi. Cái bảng mục lục bạn gửi không chỉ là danh sách các thuật ngữ; nó là một bản đồ dẫn đường qua những thất bại và thành công của hàng ngàn kỹ sư đi trước. Mỗi số trang ở đó đều đánh dấu một bài học xương máu, một lần hệ thống bị sập, hay một phát kiến vĩ đại giúp thế giới này vận hành trơn tru hơn một chút. Hy vọng đoạn văn "tào lao" nhưng đầy tâm huyết này đã giúp bạn đạt được chỉ số token mong muốn. Nó giống như một bài kiểm tra Stress test cho khả năng kiên nhẫn của bạn vậy. Nếu bạn đọc được đến tận đây mà không cảm thấy chóng mặt, thì xin chúc mừng, bạn có đủ tố chất để trở thành một chuyên gia về Software Engineering thực thụ rồi đấy – người có thể chịu đựng được những tài liệu dài dằng dặc và khô khan nhất mà vẫn tìm thấy được một chút thú vị len lỏi ở giữa các dòng chữ."""
text = text*2
# token_c = encoding.encode(text)
# print(len(token_c))
# print(token_count(text))

print_splitted(texts)