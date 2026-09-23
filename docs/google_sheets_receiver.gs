/**
 * @OnlyCurrentDoc
 */
// Google Sheet에서 확장 프로그램 > Apps Script를 열어 이 코드를 붙여 넣으세요.
// 이 코드는 시트 소유자의 계정으로 실행되는 웹 앱용입니다.
const TAB_NAME = '앱 평가';
const HEADERS = ['제출 시각', '디자인 (1~5)', '감정 도움 (1~5)', '계속 사용할 의향 (1~5)', '개선 의견', '참여 코드', '제출 ID'];

function doPost(e) {
  const lock = LockService.getScriptLock();
  let locked = false;
  try {
    const input = JSON.parse(e.postData.contents);
    const design = validScore(input.design);
    const emotion = validScore(input.emotion_helpfulness);
    const continuedUse = validScore(input.continued_use);
    const improvement = String(input.improvement || '').trim();
    const clientId = String(input.client_id || '').trim();
    const submissionId = String(input.submission_id || '').trim();
    if (!improvement || improvement.length > 500) throw new Error('개선 의견을 확인해주세요.');
    if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(clientId)) throw new Error('브라우저 식별값을 확인해주세요.');
    if (!/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(submissionId)) throw new Error('제출 식별값을 확인해주세요.');

    lock.waitLock(10000);
    locked = true;
    const book = SpreadsheetApp.getActiveSpreadsheet();
    if (!book) throw new Error('연결된 구글 시트를 찾지 못했어요.');
    let sheet = book.getSheetByName(TAB_NAME);
    if (!sheet) sheet = book.insertSheet(TAB_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS);
    } else {
      for (let column = 6; column <= 7; column += 1) {
        const existingHeader = String(sheet.getRange(1, column).getValue()).trim();
        if (existingHeader && existingHeader !== HEADERS[column - 1]) {
          throw new Error(column + '열에 이미 다른 제목이 있어요.');
        }
        if (!existingHeader) sheet.getRange(1, column).setValue(HEADERS[column - 1]);
      }
    }

    const previousSubmission = findSubmission(sheet, submissionId);
    if (previousSubmission) {
      return jsonResponse({saved: true, participant_code: previousSubmission, duplicate: true});
    }
    const participantCode = codeForClient(clientId, sheet);

    // 시트 수식으로 해석될 수 있는 의견은 일반 글자로 저장합니다.
    const safeImprovement = /^[=+\-@]/.test(improvement) ? "'" + improvement : improvement;
    sheet.appendRow([new Date(), design, emotion, continuedUse, safeImprovement, participantCode, submissionId]);
    SpreadsheetApp.flush();
    return jsonResponse({saved: true, participant_code: participantCode});
  } catch (error) {
    console.error(error);
    return jsonResponse({saved: false});
  } finally {
    if (locked) lock.releaseLock();
  }
}

function findSubmission(sheet, submissionId) {
  if (sheet.getLastRow() <= 1) return '';
  const rows = sheet.getRange(2, 6, sheet.getLastRow() - 1, 2).getValues();
  for (const row of rows) {
    if (String(row[1]).trim() === submissionId) return String(row[0]).trim();
  }
  return '';
}

function codeForClient(clientId, sheet) {
  // 임의 식별값 원문은 시트에 쓰지 않고 해시와 참여 코드의 대응만 스크립트에 보관합니다.
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, clientId, Utilities.Charset.UTF_8);
  const hash = digest.map(byte => (byte & 255).toString(16).padStart(2, '0')).join('');
  const properties = PropertiesService.getScriptProperties();
  const clientKey = 'participant:' + hash;
  const existingCode = properties.getProperty(clientKey);
  if (existingCode) return existingCode;

  let lastNumber = Number(properties.getProperty('last_participant_number') || 0);
  if (sheet.getLastRow() > 1) {
    const previousCodes = sheet.getRange(2, 6, sheet.getLastRow() - 1, 1).getValues();
    for (const row of previousCodes) {
      const match = /^U(\d+)$/.exec(String(row[0]).trim());
      if (match) lastNumber = Math.max(lastNumber, Number(match[1]));
    }
  }
  const nextNumber = lastNumber + 1;
  const code = 'U' + String(nextNumber).padStart(2, '0');
  // 먼저 번호를 예약해 저장 실패나 행 삭제 뒤에도 다른 사람에게 재발급하지 않습니다.
  properties.setProperties({[clientKey]: code, last_participant_number: String(nextNumber)});
  return code;
}

function validScore(value) {
  if (!Number.isInteger(value) || value < 1 || value > 5) {
    throw new Error('점수는 1~5 사이여야 해요.');
  }
  return value;
}

function jsonResponse(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}
