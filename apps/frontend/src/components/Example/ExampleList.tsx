import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "メンバーの「所属」を更新する手順をお教えください。",
        value: "メンバーの「所属」を更新する手順をお教えください。"
    },
    { text: "プロジェクト管理者を変更する方法を教えてください。", value: "プロジェクト管理者を変更する方法を教えてください。" },
    { text: "利用者登録しているユーザをタスクにアサインする方法を教えてください。", value: "利用者登録しているユーザをタスクにアサインする方法を教えてください。" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
