import { renderToStaticMarkup } from "react-dom/server";
import { DataPoint, getCitationFilePath } from "../../api";

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: string[];
    followupQuestions: string[];
};




export function getSourceInfomation(dataPoints: DataPoint[], ref:string): DataPoint {
    //dataPointsの配列からidが一致するものを探す
    const dataPoint = dataPoints.find((dataPoint) => dataPoint.name === ref || dataPoint.id === ref);
    return dataPoint ?? { id: "", name: "", web_url: "", hit_id: "" }; 
}

export function parseAnswerToHtml(answer: string, isStreaming: boolean, onCitationClicked: (hit_id: string, web_url: string, file_name: string) => void): HtmlParsedAnswer {
    const citations: string[] = [];
    const followupQuestions: string[] = [];

    // Extract any follow-up questions that might be in the answer
    let parsedAnswer = answer.replace(/<<([^>>]+)>>/g, (match, content) => {
        followupQuestions.push(content);
        return "";
    });

    // trim any whitespace from the end of the answer after removing follow-up questions
    parsedAnswer = parsedAnswer.trim();

    // Omit a citation that is still being typed during streaming
    if (isStreaming){
        let lastIndex = parsedAnswer.length;
        for (let i = parsedAnswer.length - 1; i >= 0; i--) {
            if (parsedAnswer[i] === ']') {
                break;
            } else if (parsedAnswer[i] === '[') {
                lastIndex = i;
                break;
            }
        }
        const truncatedAnswer = parsedAnswer.substring(0, lastIndex);
        parsedAnswer = truncatedAnswer;
    } 

    const parts = parsedAnswer.split(/\[([^\]]+)\]/g);

    const fragments: string[] = parts.map((part, index) => {
        if (index % 2 === 0) {
            return part;
        } else {
            let citationIndex: number;
            if (citations.indexOf(part) !== -1) {
                citationIndex = citations.indexOf(part) + 1;
            } else {
                citations.push(part);
                citationIndex = citations.length;
            }

            const path = getCitationFilePath(part);

            return renderToStaticMarkup(
                <a className="supContainer" title={part} onClick={() => onCitationClicked(String(citationIndex), path, part)}>
                    <sup>{citationIndex}</sup>
                </a>
            );
        }
    });

    return {
        answerHtml: fragments.join(""),
        citations,
        followupQuestions
    };
}
