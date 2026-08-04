const fs = require('fs');
const parser = require('@babel/parser');

const filePath = process.argv[2]; // Get the file path from command-line arguments

try {
    const code = fs.readFileSync(filePath, 'utf-8');
    const parsed = parser.parse(code, {
        sourceType: "module",
        plugins: [
            "jsx",
            "typescript",
            "classProperties",
            "dynamicImport",
            "optionalChaining",
            "nullishCoalescingOperator",
            "objectRestSpread",
            "exportDefaultFrom",
            "exportNamespaceFrom",
            "exportExtensions",
            "functionBind",
            "functionSent",
            "doExpressions",
            "decorators-legacy",
            "classPrivateProperties",
            "classPrivateMethods",
            "privateIn",
            "logicalAssignment",
            "numericSeparator",
            "throwExpressions",
            "partialApplication",
            ["pipelineOperator", { "proposal": "minimal" }],
            "recordAndTuple"
        ]
    });

    const classes = [];
    const functions = [];

    // Helper function to process nodes recursively
    function processNode(node) {
        if (!node) return;


        // Process different node types
        if (node.type === 'ExportNamedDeclaration' || node.type === 'ExportDefaultDeclaration') {
            if (node.declaration) {
                processNode(node.declaration);
            }
        } else if (node.type === 'ClassDeclaration') {
            const methods = [];
            node.body.body.forEach(method => {
                if (method.type === 'ClassMethod' && method.key && method.key.name) {
                    methods.push({
                        name: method.key.name,
                        start_line: method.loc.start.line,
                        end_line: method.loc.end.line
                    });
                }
            });
            classes.push({
                name: node.id ? node.id.name : 'UnnamedClass', // Check for null/undefined
                start_line: node.loc.start.line,
                end_line: node.loc.end.line,
                methods: methods,
                isExported: false
            });
        } else if (node.type === 'FunctionDeclaration') {
            if (node.id && node.id.name) {
                functions.push({
                    name: node.id.name,
                    start_line: node.loc.start.line,
                    end_line: node.loc.end.line
                });
            }
        } else if (node.type === 'AssignmentExpression') {
            const left = node.left;
            if (left && left.type === 'MemberExpression') {
                let objectName = '';
                let current = left;
                while (current && current.type === 'MemberExpression') {
                    const propertyName = current.property ? current.property.name : '';
                    objectName = objectName ? `${propertyName}.${objectName}` : propertyName;
                    current = current.object;
                }
                if (current && current.type === 'Identifier') {
                    objectName = `${current.name}.${objectName}`;
                }
                if (node.right && (node.right.type === 'FunctionExpression' || node.right.type === 'ArrowFunctionExpression')) {
                    functions.push({
                        name: objectName,
                        start_line: node.loc.start.line,
                        end_line: node.loc.end.line
                    });
                }
            }
        } else if (node.type === 'VariableDeclaration') {
            node.declarations.forEach(declaration => {
                if (declaration.init) {
                    if (declaration.init.type === 'ArrowFunctionExpression' || declaration.init.type === 'FunctionExpression') {
                        functions.push({
                            name: declaration.id ? declaration.id.name : 'UnnamedFunction', // Check for null/undefined
                            start_line: declaration.loc.start.line,
                            end_line: declaration.loc.end.line
                        });
                    }
                }
            });
        }        

    }

    // Process each node in the program body
    parsed.program.body.forEach(node => {
        processNode(node);
    });

    console.log(JSON.stringify({ classes, functions }));
} catch (error) {
    console.error(`Error parsing file ${filePath}: ${error.message}`);
    process.exit(1);
}
