# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""A battery of the ways a secret reaches a log and goes through the cleaner (each case names the part that must NOT stay), the forms that must NOT be touched (counters, states, versions, names of
repositories), and the way the two forms of a text (as it is and plain) are cleaned. The cleaner is by pattern: it lowers the risk and it is not a guarantee, so a case that cannot be caught by a pattern
(a key without its header, twenty hexadecimal digits) is not in the list."""
import unittest

import _testenv  # noqa: F401
from github_actions_monitor.integrations import ai_alerts
from github_actions_monitor.security import redactor
from github_actions_monitor.sentinels import sentinel_ai

TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"[:36]
PAT = "github_pat_" + "11ABCDEFG0abcdefghij_" + "Z" * 40
EMAIL = "victima.canario@corp-ejemplo.com"
IP = "10.20.30.40"
HOMEP = "/home/victima/proyecto/secreto.txt"
WINP = "C:\\Users\\victima\\Documents\\clave.pem"
T = TOKEN

KNOWN = [
    # (nombre, texto, subcadena que NO debe quedar)
    ("ghp clasico", f"token {T}", T),
    ("ghp pegado a guion bajo", f"x_{T}", T),
    ("ghp corto 20", "ghp_" + "ABCDEFGHIJKLMNOPQRST", "ghp_" + "ABCDEFGHIJKLMNOPQRST"),
    ("ghp con ancho cero dentro", T[:10] + "\u200b" + T[10:], T[10:]),
    ("ghp codificado % (gh%70_)", "gh%70_" + T[4:], T[4:]),
    ("ghp fullwidth prefijo", "\uff47\uff48\uff50_" + T[4:], T[4:]),
    ("ghp partido en dos lineas", T[:20] + "\n" + T[20:], T[20:]),
    ("github_pat", PAT, PAT[-30:]),
    ("url con token tras ruta github permitida", f"https://github.com/o/r/actions/runs/1?token={T}", T),
    ("url github con userinfo", f"https://x-access-token:{T}@github.com/o/r.git", T),
    ("url github solo usuario=token corto", "https://abc123tokencorto@github.com/o/r", "abc123tokencorto"),
    ("subdominio parecido", f"https://github.com.evil.example/{T}", T),
    ("url otra con user:pass", "https://deploy:Sup3rS3cret@registry.example.com/v2", "Sup3rS3cret"),
    ("url con pass que lleva @ codificada", "https://deploy:Sup3r%40S3cret@registry.example.com/v2", "S3cret"),
    ("url solo usuario (token como usuario)", "https://Sup3rS3cretTok@registry.example.com/v2", "Sup3rS3cretTok"),
    ("Authorization Basic corto", "Authorization: Basic dTpwYXNz", "dTpwYXNz"),
    ("Authorization token opaco corto", "Authorization: token abcDEF123456", "abcDEF123456"),
    ("Authorization Bearer", "Authorization: Bearer abcdefghijklmnop", "abcdefghijklmnop"),
    ("cabecera X-Api-Key", "X-Api-Key: abcDEF123456xyz", "abcDEF123456xyz"),
    ("cabecera Cookie de sesion", "Cookie: session=abcDEF123456xyz", "abcDEF123456xyz"),
    ("password=valor", "DB_PASSWORD=hunter2hunter2", "hunter2hunter2"),
    ("password con espacio (--password valor)", "mysql --password hunter2hunter2 -h db", "hunter2hunter2"),
    ("-p pegado", "mysql -uroot -phunter2hunter2", "hunter2hunter2"),
    ("password: frase con espacios", "password: correct horse battery staple", "horse battery staple"),
    ("comillas escapadas", 'password="ab\\"cd SECRETO-FINAL"', "SECRETO-FINAL"),
    ("clave JSON con comillas", '{"password": "hunter2hunter2"}', "hunter2hunter2"),
    ("password codificado %3D", "password%3Dhunter2hunter2", "hunter2hunter2"),
    ("PASSWORD en mayusculas con dos puntos", "PASSWORD : hunter2hunter2", "hunter2hunter2"),
    ("variable sin palabra clave (DSN=...)", "SENTRY_DSN=abc123def456ghi", "abc123def456ghi"),
    ("clave con nombre 'key' a secas", "ENCRYPTION_KEY=abc123def456ghi", "abc123def456ghi"),
    ("credenciales (creds=)", "AWS_CREDS=abc123def456ghi", "abc123def456ghi"),
    ("base64 de un token (48)", "Z2hwX0ExYjJDM2Q0RTVmNkc3aDhJOWowSzFsMk0zbjRPNXA2UTdyOA==", "Z2hwX0ExYjJDM2Q0"),
    ("base64 corto de user:pass (16)", "dXNlcjpwYXNzd29yZA==", "dXNlcjpwYXNzd29yZA"),
    ("PEM completo", "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nabc\n-----END RSA PRIVATE KEY-----", "MIIEow"),
    ("PEM OPENSSH minusculas en cabecera", "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk\n-----END OPENSSH PRIVATE KEY-----", "b3BlbnNzaC1rZXk"),
    ("PEM EC con guiones largos unicode", "\u2014\u2014BEGIN EC PRIVATE KEY\u2014\u2014\nMHcCAQEE\n", "MHcCAQEE"),
    ("PEM 'BEGIN PGP PRIVATE KEY BLOCK'", "-----BEGIN PGP PRIVATE KEY BLOCK-----\nlQOYBF\n-----END PGP PRIVATE KEY BLOCK-----", "lQOYBF"),
    ("JWT", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.abcdefghijkl", "eyJzdWIiOiIxMjM0In0"),
    ("correo", EMAIL, EMAIL),
    ("correo con arroba fullwidth", "victima\uff20corp-ejemplo.com", "corp-ejemplo.com"),
    ("correo ofuscado [at]", "victima [at] corp-ejemplo.com", "corp-ejemplo.com"),
    ("IPv4", IP, IP),
    ("IPv6 comprimida", "fe80::1ff:fe23:4567:890a", "fe23:4567"),
    ("IPv6 corta ::1 con puerto", "http://[2001:db8::7]:8080/x", "2001:db8::7"),
    ("nombre interno (host privado)", "db01.interna.corp.lan:5432", "db01.interna.corp.lan"),
    ("home linux", HOMEP, "victima"),
    ("home windows", WINP, "victima"),
    ("home windows con barras normales", "C:/Users/victima/Documents/x", "victima"),
    ("home en ruta UNC", "\\\\servidor\\Users\\victima\\x", "victima"),
    ("home de root / perfil de servicio", "/root/.ssh/id_ed25519 y /var/lib/jenkins/secrets/master.key", "/root/.ssh"),
    ("usuario en /mnt/c/Users", "/mnt/c/Users/victima/x", "victima"),
    ("slack webhook", "https://hooks.slack.com/services/T000/B000/XXXXXXXXXXXXXXXXXXXXXXXX", "XXXXXXXXXXXXXXXXXXXXXXXX"),
    ("discord webhook", "https://discord.com/api/webhooks/123456789/abcDEF-ghi_JKL", "abcDEF-ghi_JKL"),
    ("teams webhook (office.com)", "https://corp.webhook.office.com/webhookb2/11111111-2222@3333/IncomingWebhook/abcdef0123456789abcd/9999", "abcdef0123456789abcd"),
    ("ntfy topic secreto", "https://ntfy.sh/mi-topic-secreto-9f3a", "mi-topic-secreto-9f3a"),
    ("telegram bot", "https://api.telegram.org/bot123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw/sendMessage", "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"),
    ("clave Anthropic", "sk-ant-api03-abcdefghijklmnopqrstuvwx", "abcdefghijklmnopqrstuvwx"),
    ("clave Google AIza", "AIzaSyA1234567890abcdefghijklmnopqrstu", "1234567890abcdefghijkl"),
    ("clave Stripe sk_live", "sk_live_abcdefghijklmnopqrstuvwx", "abcdefghijklmnopqrstuvwx"),
    ("AWS secret (40 base64 con /)", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "bPxRfiCYEXAMPLEKEY"),
    ("token de 31 hex (uuid sin guiones corto)", "0123456789abcdef0123456789abcde", "0123456789abcdef0123456789abcde"),
    ("uuid con guiones (id de cliente/secret Azure)", "client_secret 3f2a1b4c-5d6e-7f80-9a1b-2c3d4e5f6a7b", "3f2a1b4c-5d6e-7f80-9a1b-2c3d4e5f6a7b"),
]

FORMS = [
    ("DB_PASS= (sufijo PASS, sin 'word')", "DB_PASS=hunter2hunter2", "hunter2hunter2"),
    ("SMTP_PASS en YAML", "SMTP_PASS: hunter2hunter2", "hunter2hunter2"),
    ("docker login -p", "docker login -u deploy -p hunter2hunter2 registry.example.com", "hunter2hunter2"),
    ("sshpass -p con espacio", "sshpass -p hunter2hunter2 ssh deploy@host", "hunter2hunter2"),
    ("curl -u usuario:clave", "curl -u admin:hunter2hunter2 https://api.example.com/v1", "hunter2hunter2"),
    ("curl --user usuario:clave", "curl --user admin:hunter2hunter2 https://api.example.com/v1", "hunter2hunter2"),
    (".netrc (password valor)", "machine api.example.com login deploy password hunter2hunter2", "hunter2hunter2"),
    (".pgpass", "db.example.com:5432:app:deploy:hunter2hunter2", "hunter2hunter2"),
    (".npmrc _auth=", "//registry.example.com/:_auth=ZGVwbG95Omh1bnRlcjI=", "ZGVwbG95Omh1bnRlcjI"),
    ("gradle storePassword valor", "storePassword hunter2hunter2", "hunter2hunter2"),
    ("KEYSTORE_PASS", "KEYSTORE_PASS=hunter2hunter2", "hunter2hunter2"),
    ("contrasena en espanol", "contraseña: hunter2hunter2", "hunter2hunter2"),
    ("clave= en espanol", "clave=hunter2hunter2", "hunter2hunter2"),
    ("Hugging Face hf_", "hf_abcdefghijklmnopqrstuvwxyzABCDEFGH", "abcdefghijklmnopqrstuvwxyz"),
    ("Docker Hub dckr_pat_", "dckr_pat_abcdefghijklmnopqrstuvwxyzA", "abcdefghijklmnopqrstuvwxyz"),
    ("Stripe whsec_", "whsec_abcdefghijklmnopqrstuvwxyz012345", "abcdefghijklmnopqrstuvwxyz"),
    ("Google OAuth GOCSPX-", "GOCSPX-abcdefghijklmnopqrstuvwxyz01", "abcdefghijklmnopqrstuvwxyz"),
    ("Slack xapp-", "xapp-1-A0000000000-0000000000000-abcdefabcdef", "abcdefabcdef"),
    ("telegram token sin 'bot'", "TG=123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"),
    ("url con clave que lleva @ sin codificar", "https://deploy:Sup3r@S3cretTail@10.1.2.3/v2", "S3cretTail"),
    ("ruta Windows con barras dobles (repr/JSON)", "open('C:\\\\Users\\\\victima\\\\proyecto\\\\x.txt')", "victima"),
    ("str(FileNotFoundError) de una ruta de Windows", str(FileNotFoundError(2, "No such file or directory", "C:\\Users\\victima\\proyecto\\x.txt")), "victima"),
    ("carpeta personal de macOS en minusculas /users", "/users/victima/x", "victima"),
    ("home en variable ~victima", "cd ~victima/proyecto", "victima"),
    ("X-Auth: corto", "X-Auth: abcDEF123456", "abcDEF123456"),
    ("session id en query", "https://ci.example.com/job?sid=abcDEF123456xyz&jsessionid=QWERTY123456", "QWERTY123456"),
    ("AWS secret tras texto (aws_secret=... cubierto?)", "aws configure set aws_secret_access_key wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "bPxRfiCYEXAMPLEKEY"),
    ("basic auth en base64 dentro de JSON 'auth'", '{"auths": {"registry.example.com": {"auth": "ZGVwbG95Omh1bnRlcjI="}}}', "ZGVwbG95Omh1bnRlcjI"),
    ("PIN/OTP", "otp=493817 pin: 2468", "493817"),
    ("IPv4 con ceros de relleno / puerto pegado", "connect 010.020.030.040:5432", "010.020.030.040"),
    ("correo con IDN", "victima@ejemplo.españa", "victima@"),
    ("correo dentro de mailto codificado", "mailto:victima%40corp-ejemplo.com", "corp-ejemplo.com"),
]

UNTOUCHED = (
    "secret_scanning: disabled", "max_tokens=500 temperature=0.1", "tokens: 1200 in, 300 out", "secrets 0\u21921", "author: Ana", "Token expired at 10:00:00", "keyboard: es", "monkey: 3",
    "sort_key=name", "cache-key: linux-pip-3.11", "primary_key: id", "hotkey=F5", "step 'Check api_key: present' failed", "at 2026-11-17T08:00:00Z", "10:00:00", "version 2.0.8.1", "v1.2.3.4",
    "errors: 12:30:45:11", "https://api.github.com/users/octocat", "https://github.com/o/r/actions/runs/123456789", "999.1.2.3",
)


class TheCleanerOnKnownForms(unittest.TestCase):
    def test_the_battery_of_known_forms_leaks_nothing_through_the_three_entrances(self):
        entrances = {"redactor": redactor.redact, "ai_alerts": ai_alerts.redact, "sentinel_ai": lambda text: sentinel_ai.sanitize_text(text, 5000)}
        leaks = []
        for name, text, needle in KNOWN + FORMS:
            for label, clean in entrances.items():
                if needle in clean(text):
                    leaks.append((label, name))
        self.assertEqual(leaks, [])

    def test_what_is_not_a_secret_is_not_touched(self):
        for text in UNTOUCHED:
            self.assertEqual(redactor.redact(text), text, text)

    def test_the_double_bars_of_a_windows_path_do_not_hide_the_name(self):
        error = str(FileNotFoundError(2, "No such file or directory", "C:\\Users\\victima\\proyecto\\x.txt"))
        self.assertNotIn("victima", redactor.redact(error))
        self.assertNotIn("victima", redactor.redact(repr(error)))
        self.assertNotIn("victima", redactor.redact("C:\\\\Users\\\\victima\\\\x"))

    def test_a_secret_seen_only_in_the_plain_form_goes_even_with_a_decoy_that_is_seen_only_as_it_is(self):
        for text, needle in (("ghp\u200b_" + TOKEN[4:] + " pwd=%20", TOKEN[4:]), ("to victima%40corp-ejemplo.com pwd=%20", "corp-ejemplo.com"),
                             ("\uff47\uff48\uff50_" + TOKEN[4:] + " key=%09", TOKEN[4:])):
            self.assertNotIn(needle, redactor.redact(text).replace("\u200b", ""), text)


class TheStructureKeepsWhatIsNotASecret(unittest.TestCase):
    def test_two_keys_that_look_the_same_once_cleaned_are_both_kept(self):
        out = redactor.redact_data({"0123456789abcdef0123456789abcdef01234567": {"repo": "one"}, "89abcdef0123456789abcdef0123456789abcdef": {"repo": "two"}})
        self.assertEqual(sorted(v["repo"] for v in out.values()), ["one", "two"])
        mails = redactor.redact_data({"ana@corp-ejemplo.com": 3, "luis@corp-ejemplo.com": 5})
        self.assertEqual(sorted(mails.values()), [3, 5])

    def test_a_state_a_counter_or_a_repository_named_like_a_secret_stays(self):
        for sample in ({"credential": "blind"}, {"token_state": "expired"}, {"secret_scanning": "disabled"}, {"password_policy": "strong"}, {"cookie_banner": "shown"}, {"tokens_in": "1200"},
                       {"by_repo": {"token-tools": "failure", "secret-santa": "success"}}, {"api_key_env": "OPENAI_API_KEY"}):
            self.assertEqual(redactor.redact_data(sample), sample)

    def test_a_key_that_says_secret_still_hides_its_value(self):
        for key in ("password", "api_key", "access_token", "x-token", "client_secret", "Authorization", "cookie", "db_pwd"):
            self.assertEqual(redactor.redact_data({key: "hunter2hunter2"}), {key: "[secret]"}, key)


if __name__ == "__main__":
    unittest.main()
