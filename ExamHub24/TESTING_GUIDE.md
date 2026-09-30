# ExamHub24 — Full Testing Guide

Ye guide follow karke aap poora platform real-time run karke, har module ko end-to-end
test kar sakte ho. Har step ke saath **expected result** diya gaya hai — agar wo nahi
milta, to us step ke paas bug hai.

---

## Part 0 — Setup (ek baar karna hai)

```bash
# 1. Virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Dependencies install
pip install -r requirements.txt

# 3. .env file
cp .env.example .env
# .env kholke SECRET_KEY mein koi bhi random long string daal do

# 4. Database setup
python manage.py makemigrations
python manage.py migrate

# 5. Admin account
python manage.py createsuperuser
# username/email/password set karo — ye baad mein /admin/ login ke liye chahiye

# 6. Demo data seed karo (IMPORTANT — isse testing bahut fast hogi)
python manage.py seed_demo_data

# 7. Server start
python manage.py runserver
```

Agar sab sahi gaya to terminal mein "Starting development server at
http://127.0.0.1:8000/" dikhega — bas isko tab tak chalta chhod do jab tak testing kar rahe ho.

**Common errors yahan hi:**

- `ModuleNotFoundError` → step 2 (pip install) dobara karo, virtual environment activate hai ya nahi check karo.
- `django.db.utils.OperationalError` → step 4 (makemigrations + migrate) dobara karo.
- Agar koi bhi error aaye jo samajh na aaye, poora error message paste kar dena, main fix bata dunga.

---

## Part 1 — Public Pages (bina login ke)

| # | Action | URL | Expected Result |
|---|--------|-----|------------------|
| 1 | Homepage kholo | `/` | "Banking" category card dikhe, "IBPS PO Free Mock Series" free test series mein dikhe, 3 current affairs articles dikhein |
| 2 | Exam categories | `/exams/` | "Banking" category card dikhe |
| 3 | Category click karo | — | "IBPS PO" exam card dikhe |
| 4 | Exam click karo | — | "Quantitative Aptitude" subject list mein, aur test series section mein "IBPS PO Free Mock Series" dikhe |
| 5 | Test series list | `/mock-tests/` | "IBPS PO Free Mock Series" dikhe, badge "Free" ho |
| 6 | Current Affairs | `/current-affairs/` | 3 articles dikhein, category filter buttons (National/Economy/Sports) kaam karein |
| 7 | Subscription Plans | `/subscriptions/` | Silver/Gold/Platinum — 3 plans dikhein with features |
| 8 | Study Material link click karo | `/study-material/` | Login required page par redirect ho (kyunki `@login_required` hai) |

---

## Part 2 — Registration & OTP (naya account)

1. Navbar mein **Sign Up** click karo.
2. Form fill karo (naya username/email/phone — demo_student wale use mat karna).
3. Submit karo.
4. **Expected:** "Please verify the OTP..." message dikhe, OTP verify page par redirect ho.
5. **Terminal check karo** — kyunki `.env` mein console email backend set hai, OTP terminal mein print hoga. Kuch aisa dikhega:
   ```
   Subject: ExamHub24 — Verify your account
   Your OTP is 123456...
   ```
6. Wo 6-digit OTP form mein daalo, submit karo.
7. **Expected:** "Account verified successfully!" message, seedha Dashboard par redirect ho jao — matlab login bhi ho gaya.

**Edge case test:** Galat OTP daal ke dekho → "Invalid or expired OTP" error aana chahiye.

---

## Part 3 — Login (seeded demo account se)

1. Logout karo (agar login ho).
2. Login page par jao, credentials:
   - **Username:** `demo_student`
   - **Password:** `DemoPass@123`
3. **Expected:** Dashboard par redirect, "Welcome back, Demo Student!" dikhe.

**Edge case test:** Galat password se login try karo → error message aana chahiye, login fail ho.

---

## Part 4 — Profile

1. Navbar mein apna naam/icon click karo → Profile page.
2. Naam, phone, DOB, target exam edit karo, profile picture upload karo (optional).
3. Save karo.
4. **Expected:** "Profile updated successfully" message, changes reflect hon.

---

## Part 5 — Mock Test Attempt (SABSE IMPORTANT FLOW)

Ye test-taking engine hai — is guide ka sabse critical part.

1. `/mock-tests/` par jao → "IBPS PO Free Mock Series" → "View Tests".
2. "Quantitative Aptitude — Mock Test 1" ke saamne **Start** click karo.
3. Instructions page dikhegi (10 questions, 15 minutes, negative marking).
4. Checkbox tick karo, **Start Test** click karo.

**Ab test-attempt screen par ho — ye check karo:**

| Check | Expected |
|---|---|
| Navbar/footer | Gayab hone chahiye (distraction-free exam mode) |
| Timer (top-right) | 15:00 se countdown shuru ho, har second decrease ho |
| Question palette (right side) | 10 numbered buttons, sab "not visited" (white) se start hon |
| Question 1 | Text + 4 options (radio buttons) dikhein |

**Ab actual answering test karo:**

5. Question 1 ka koi bhi option select karo → **Save & Next** click karo.
   - **Expected:** Palette mein button 1 **green (answered)** ho jaye, Question 2 dikhe.
6. Question 2 par **kuch select na karke** seedha **Save & Next** click karo.
   - **Expected:** Palette button 2 **red (not answered)** rahe.
7. Question 3 par option select karke **Mark for Review & Next** click karo.
   - **Expected:** Palette button 3 **yellow (marked)** ho jaye.
8. Palette mein directly button 7 click karo (bina 4,5,6 attempt kiye).
   - **Expected:** Seedha Question 7 par navigate ho, aur beech ke questions "not answered" (red) status mein aa jayein (kyunki visit ho chuke honge).
9. Kisi answered question par wapas jao, **Clear Response** click karo.
   - **Expected:** Selection clear ho, palette status "not answered" ho jaye.
10. **Previous** button test karo — pichle question par jana chahiye.

**Auto-save test (bahut important):**

11. 5-6 questions answer karo, phir **browser ko refresh mat karo** — seedha naya tab mein `/dashboard/` khol ke wapas test tab par aao.
12. Test tab par koi bhi action karo (jaise Save & Next).
13. Ab **Submit Test** click karo (confirm popup aayega, "OK" karo).
14. **Expected:** Result page par redirect ho.

**Result page par check karo:**

| Check | Expected |
|---|---|
| Score | Jitne correct utna +1, jitne wrong utna -0.25 (negative marking) ka net total |
| Correct/Wrong/Unattempted counts | Aapke actual answers se match karein |
| Accuracy % | (Correct / Attempted) * 100 |
| Rank | "#1 / 1" (kyunki abhi sirf aapne attempt kiya hai) |
| Solutions section | Har question ke neeche correct option **green** mein, agar aapka answer galat tha to wo **red** mein highlight ho, explanation dikhe |

**Auto-submit test (alag se, dobara test attempt karke):**

15. Wapas dashboard se same test dobara start karo (naya attempt banega).
16. Kuch questions answer karke, is baar **kuch mat karo — bas wait karo** jab tak timer khatam na ho jaye (15 min lagenge — chahen to `mock_tests/models.py` mein `duration_minutes` temporarily 1 minute kar sakte ho testing ke liye, phir wapas revert kar dena).
17. **Expected:** Timer 00:00 hote hi, browser confirm popup ke bina hi test automatically submit ho jaye, result page par redirect ho, status "Auto Submitted" ho (admin panel mein `TestAttempt` check karke dekh sakte ho).

---

## Part 6 — Results & Leaderboard

1. `/results/history/` par jao.
2. **Expected:** Dono attempts (manual submit + auto-submit) list mein dikhein, score/accuracy/rank ke saath.
3. Kisi result par "View" click karo → wahi result detail page khulna chahiye.
4. Result page se "View Leaderboard" click karo.
5. **Expected:** Aapki dono entries (agar dono completed hain) rank ke hisaab se sorted dikhein, aapki row highlight (halka blue) ho.

---

## Part 7 — Dashboard & Analytics

1. `/dashboard/` par jao.
2. Check karo:
   - "Tests Attempted" count sahi ho (jitni baar submit kiya)
   - "Subject-wise Performance" mein "Quantitative Aptitude" ka progress bar dikhe
   - Agar accuracy kam hai (jaise galat answers zyada diye), progress bar **red/yellow** dikhna chahiye; zyada accuracy par **green**
   - Agar 3+ questions ek particular tag (jaise "Percentage") se attempt kiye aur unme se zyada galat kiye, to "Weak: Percentage" jaisa text dikhna chahiye
3. "Recent Results" table mein latest attempt dikhe, click karke result page khule.

---

## Part 8 — Subscription & Payment (Demo Mode)

Chunki `.env` mein Razorpay keys khaali hain, payment **demo mode** mein chalega (turant success simulate hoga) — ye normal hai, real gateway ke bina testing ke liye yehi expected hai.

1. `/subscriptions/` par jao, koi bhi plan (jaise "Silver Monthly") choose karo.
2. Plan detail page par "Proceed to Pay" click karo.
3. **Expected:** Turant "Payment Successful!" page dikhe (demo mode message ke saath), "Demo payment successful..." wala message dikhe.
4. Navbar/dashboard mein check karo → **"Premium Member"** badge dikhna chahiye ab.
5. Admin panel (`/admin/`) → Payments → Orders mein check karo → naya Order status "Success" ho.
6. Admin panel → Subscriptions → User Subscriptions mein naya record dikhe, `end_date` sahi (plan ke duration ke hisaab se) ho.

**Premium-gating test:**

7. Admin panel se ek **naya MockTest** banao jiski series `is_free = False` ho (ya existing series ko premium bana do temporarily).
8. Us test ko **logout karke ek naye/non-premium account** se open karne ki koshish karo.
9. **Expected:** "This test is part of a premium series..." warning ke saath Plans page par redirect ho.
10. Ab premium account (jisne payment kiya) se try karo → test open hona chahiye.

---

## Part 9 — Study Material

1. Admin panel → Study Material → "Add Study Material" → ek PDF upload karo (koi bhi sample PDF), subject select karo, `is_premium = False` rakho.
2. `/study-material/` par jao → material dikhna chahiye, "Download" click karke file download honi chahiye.
3. Ek aur material `is_premium = True` ke saath add karo → non-premium account se download try karo → Plans page par redirect hona chahiye.

---

## Part 10 — Notifications

1. Koi bhi test submit karo (Part 5 se).
2. `/notifications/` par jao.
3. **Expected:** "Result Declared" title wali notification dikhe, message mein score aur rank mention ho.
4. Dashboard par bhi "New Notifications" count aur preview dikhna chahiye (jab tak notifications page visit na ho, tab tak unread rahegi).

---

## Part 11 — Admin Panel (`/admin/`)

Superuser se login karke check karo:

| Section | Test |
|---|---|
| Users | Demo student aur naya registered user dikhein, "Premium" column sahi ho |
| Questions | Naya question add karo — subject, 4 options, correct answer, save karo → questions list mein dikhe |
| Mock Tests | Ek test open karo → "Test Questions" inline section mein questions add/remove karo |
| Test Attempts | Sab attempts dikhein, "readonly" score fields edit na ho paayein (design ke mutabik) |
| Orders | Payment records dikhein |

Custom admin overview bhi check karo: `/dashboard/admin-overview/` (sirf staff/superuser access kar sakte hain) — total users, revenue, tests conducted ke stats dikhne chahiye.

---

## Part 12 — Password Reset Flow

1. Logout karo, Login page se "Forgot password?" click karo.
2. Apna email daalo, submit karo.
3. **Terminal check karo** — reset link console mein print hogi (jaise OTP).
4. Wo link browser mein open karo, naya password set karo.
5. Naye password se login karke confirm karo.

---

## Quick Bug-Report Checklist

Agar kahin issue mile, ye batana taaki main jaldi fix kar sakoon:
1. Kaunsa step (is guide ke Part number ke saath)
2. Kya expected tha vs kya hua
3. Terminal mein koi error message (poora traceback paste kar dena)
4. Browser console mein koi JS error (F12 → Console tab)
