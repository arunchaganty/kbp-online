from logging.handlers import SMTPHandler

class CustomSMTPHandler(SMTPHandler):
  def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            from email.message import EmailMessage
            import email.utils

            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port, timeout=self.timeout)
            msg = EmailMessage()
            msg['From'] = self.fromaddr
            msg['To'] = ','.join(self.toaddrs)
            msg['Subject'] = self.getSubject(record)
            msg['Date'] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.secure is not None:
                smtp.ehlo()
                smtp.starttls(*self.secure)
                smtp.ehlo()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)
            smtp.quit()
        except Exception:
            self.handleError(record)
